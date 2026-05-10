from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

import telebot
from telebot import types

from app.bot.keyboards import inline_options, main_menu, time_keyboard, yes_no_keyboard
from app.config import Settings
from app.models import AirtableRecord, OrderDraft
from app.services.ai import AssistantService
from app.services.business import BusinessRules
from app.services.documents import DocumentService
from app.services.notifications import NotificationService
from app.services.repository import Repository


class BotHandlers:
    def __init__(self, bot: telebot.TeleBot, settings: Settings, repository: Repository, assistant: AssistantService, documents: DocumentService) -> None:
        self.bot = bot
        self.settings = settings
        self.repository = repository
        self.assistant = assistant
        self.documents = documents
        self.rules = BusinessRules(settings)
        self.notifications = NotificationService(bot, repository, settings.accountant_telegram_ids)
        self.auth_waiting: set[int] = set()
        self.drafts: dict[int, OrderDraft] = {}
        self.waiting_quantity: dict[int, str] = {}
        self.waiting_comment: set[int] = set()
        self.register()

    def register(self) -> None:
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(commands=['help'])(self.help)
        self.bot.message_handler(commands=['cancel'])(self.cancel)
        self.bot.message_handler(func=lambda message: True, content_types=['text'])(self.text)
        self.bot.callback_query_handler(func=lambda call: True)(self.callback)

    def start(self, message: types.Message) -> None:
        telegram_id = message.from_user.id
        if self._is_admin(telegram_id):
            self.bot.send_message(message.chat.id, 'Панель администратора открыта.', reply_markup=main_menu())
            return
        client = self.repository.find_client_by_telegram_id(telegram_id)
        if client:
            self.bot.send_message(message.chat.id, f'Здравствуйте, {client.get("name", "клиент")}! Выберите действие.', reply_markup=main_menu())
            return
        self.auth_waiting.add(telegram_id)
        self.bot.send_message(message.chat.id, 'Введите код доступа, например COFFEE001.')

    def help(self, message: types.Message) -> None:
        self.bot.send_message(message.chat.id, self._help_text(), reply_markup=main_menu())

    def cancel(self, message: types.Message) -> None:
        self.drafts.pop(message.from_user.id, None)
        self.waiting_quantity.pop(message.from_user.id, None)
        self.waiting_comment.discard(message.from_user.id)
        self.bot.send_message(message.chat.id, 'Действие отменено.', reply_markup=main_menu())

    def text(self, message: types.Message) -> None:
        telegram_id = message.from_user.id
        text = message.text.strip()
        if telegram_id in self.auth_waiting:
            self._handle_access_code(message, text)
            return
        client = self.repository.find_client_by_telegram_id(telegram_id)
        if not client and not self._is_admin(telegram_id):
            self.auth_waiting.add(telegram_id)
            self.bot.send_message(message.chat.id, 'Сначала авторизуйтесь. Введите код доступа.')
            return
        if text == '🛒 Сделать заказ':
            self._start_order(message, client)
        elif text == '🔁 Мой последний заказ':
            self._last_order(message, client)
        elif text == '📜 История заказов':
            self.bot.send_message(message.chat.id, 'История хранится в Airtable в таблице Orders. В MVP вывод последних заказов можно расширить под ваш формат.')
        elif text == '❓ Помощь':
            self.help(message)
        elif text == '☎️ Связаться с менеджером':
            self.bot.send_message(message.chat.id, f'Менеджер: {self.settings.manager_contact}')
        elif telegram_id in self.waiting_quantity:
            self._handle_quantity(message, text)
        elif telegram_id in self.waiting_comment:
            self._handle_comment(message, text)
        else:
            self._handle_free_text_order(message, client, text)

    def callback(self, call: types.CallbackQuery) -> None:
        action, _, value = call.data.partition(':')
        telegram_id = call.from_user.id
        draft = self.drafts.get(telegram_id)
        if action == 'category' and draft:
            draft.selected_category = value
            products = self.repository.list_products_by_category(value)
            options = [(str(product.get('name', 'Товар')), product.id) for product in products]
            self.bot.edit_message_text('Выберите товар:', call.message.chat.id, call.message.message_id, reply_markup=inline_options('product', options))
        elif action == 'product' and draft:
            product = self.repository.get_product(value)
            self.waiting_quantity[telegram_id] = product.id
            self.bot.send_message(call.message.chat.id, f'Введите количество для товара «{product.get("name", "")}» числом.')
        elif action == 'more' and draft:
            if value == 'yes':
                self._ask_category(call.message.chat.id)
            else:
                self.bot.send_message(call.message.chat.id, 'Выберите интервал доставки:', reply_markup=time_keyboard())
        elif action == 'time' and draft:
            draft.delivery_time = value
            self.waiting_comment.add(telegram_id)
            self.bot.send_message(call.message.chat.id, 'Введите комментарий к заказу или отправьте «-».')
        elif action == 'confirm' and draft:
            if value == 'yes':
                self._finalize_order(call.message.chat.id, telegram_id)
            else:
                self.drafts.pop(telegram_id, None)
                self.waiting_quantity.pop(telegram_id, None)
                self.waiting_comment.discard(telegram_id)
                self.bot.send_message(call.message.chat.id, 'Заказ отменен.', reply_markup=main_menu())
        self.bot.answer_callback_query(call.id)

    def _handle_access_code(self, message: types.Message, code: str) -> None:
        telegram_id = message.from_user.id
        client = self.repository.find_client_by_access_code(code)
        if not client:
            self.bot.send_message(message.chat.id, 'Код не найден или клиент отключен. Проверьте код и попробуйте снова.')
            return
        existing_telegram_id = client.get('telegram_id')
        if existing_telegram_id and int(existing_telegram_id) != telegram_id:
            self.bot.send_message(message.chat.id, 'Этот код уже привязан. Попросите администратора сбросить привязку.')
            return
        self.repository.bind_client_telegram(client.id, telegram_id)
        self.auth_waiting.discard(telegram_id)
        self.bot.send_message(message.chat.id, f'Готово! Доступ открыт для {client.get("name", "клиента")}.', reply_markup=main_menu())

    def _start_order(self, message: types.Message, client: AirtableRecord | None) -> None:
        if not client:
            return
        draft = OrderDraft(client_record_id=client.id, delivery_date=self.rules.earliest_delivery_date())
        self.drafts[message.from_user.id] = draft
        self._ask_category(message.chat.id)

    def _ask_category(self, chat_id: int) -> None:
        categories = self.repository.list_categories()
        self.bot.send_message(chat_id, 'Выберите категорию:', reply_markup=inline_options('category', [(item, item) for item in categories]))

    def _handle_quantity(self, message: types.Message, text: str) -> None:
        telegram_id = message.from_user.id
        product_id = self.waiting_quantity.pop(telegram_id)
        draft = self.drafts[telegram_id]
        try:
            quantity = Decimal(text.replace(',', '.'))
        except InvalidOperation:
            self.waiting_quantity[telegram_id] = product_id
            self.bot.send_message(message.chat.id, 'Количество должно быть числом. Например: 12 или 5.5')
            return
        if quantity <= 0:
            self.waiting_quantity[telegram_id] = product_id
            self.bot.send_message(message.chat.id, 'Количество должно быть больше нуля.')
            return
        if quantity >= 500:
            self.bot.send_message(message.chat.id, '⚠️ Проверьте количество: оно сильно выше обычного. Если верно — продолжайте подтверждение.')
        product = self.repository.get_product(product_id)
        draft.items.append(self.repository.product_to_cart_item(product, quantity))
        self.bot.send_message(message.chat.id, 'Товар добавлен. Добавить еще товар?', reply_markup=yes_no_keyboard('more'))

    def _handle_comment(self, message: types.Message, text: str) -> None:
        telegram_id = message.from_user.id
        self.waiting_comment.discard(telegram_id)
        draft = self.drafts[telegram_id]
        draft.comment = '' if text == '-' else text
        self.bot.send_message(message.chat.id, draft.as_summary(), reply_markup=yes_no_keyboard('confirm'))

    def _handle_free_text_order(self, message: types.Message, client: AirtableRecord | None, text: str) -> None:
        if not client:
            return
        parsed = self.assistant.parse_order_text(text, datetime.now(self.settings.tzinfo).date())
        if not parsed:
            self.bot.send_message(message.chat.id, 'Не понял заявку. Нажмите «Сделать заказ» или напишите: «Нужны 10 молока на завтра утром».')
            return
        draft = OrderDraft(
            client_record_id=client.id,
            delivery_date=self.rules.normalize_delivery_date(parsed.delivery_date),
            delivery_time=parsed.delivery_time,
            comment=parsed.comment,
        )
        products = self.repository.list_active_products()
        for parsed_item in parsed.items:
            product = self._find_product_by_name(products, parsed_item.name)
            if product:
                draft.items.append(self.repository.product_to_cart_item(product, parsed_item.quantity))
        if not draft.items:
            self.bot.send_message(message.chat.id, 'Не нашел товары из текста в Airtable. Проверьте названия товаров.')
            return
        self.drafts[message.from_user.id] = draft
        if not draft.delivery_time:
            self.bot.send_message(message.chat.id, 'Выберите интервал доставки:', reply_markup=time_keyboard())
            return
        self.bot.send_message(message.chat.id, draft.as_summary(), reply_markup=yes_no_keyboard('confirm'))

    def _finalize_order(self, chat_id: int, telegram_id: int) -> None:
        draft = self.drafts.pop(telegram_id)
        client = self.repository.find_client_by_telegram_id(telegram_id)
        if not client:
            self.bot.send_message(chat_id, 'Клиент не найден.')
            return
        order = self.repository.create_order(draft)
        self.repository.create_order_items(order.id, draft.items)
        driver = self.repository.find_driver_for_client(client)
        self.repository.create_route(draft.delivery_date, client.id, driver.id if driver else None)
        invoice = self.documents.create_invoice_html(order, client, driver, draft)
        self.repository.create_invoice(invoice.invoice_number, order.id, driver.id if driver else None, invoice.public_link)
        self.notifications.notify_suppliers(order, client, draft)
        self.notifications.notify_driver(driver, client, draft, invoice.public_link)
        self.notifications.notify_accountants(order, client, draft, invoice.public_link)
        self.bot.send_message(chat_id, f'✅ Заказ принят! Номер: {order.get("order_id", order.id)}\nНакладная: {invoice.public_link}', reply_markup=main_menu())

    def _last_order(self, message: types.Message, client: AirtableRecord | None) -> None:
        if not client:
            return
        order = self.repository.latest_order_for_client(client.id)
        if not order:
            self.bot.send_message(message.chat.id, 'Прошлых заказов пока нет.')
            return
        self.bot.send_message(message.chat.id, f'Последний заказ: {order.get("order_id", order.id)}\nДата доставки: {order.get("delivery_date", "—")}\nСтатус: {order.get("status", "—")}\nСумма: {order.get("total_sum", 0)} ₸')

    def _is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.settings.admin_telegram_ids

    @staticmethod
    def _find_product_by_name(products: list[AirtableRecord], name: str) -> AirtableRecord | None:
        needle = name.lower()
        for product in products:
            if needle in str(product.get('name', '')).lower():
                return product
        return None

    @staticmethod
    def _help_text() -> str:
        return '\n'.join([
            'Команды:',
            '/start — авторизация или главное меню',
            '/cancel — отменить текущий заказ',
            'Можно создать заказ кнопками или текстом: «Нужны 10 молока и 3 сливок на завтра утром».',
            'Заявки после 00:00 переносятся на следующую доступную дату.',
        ])
