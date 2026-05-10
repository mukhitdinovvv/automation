# Telegram-бот автоматизации поставок продуктов

Готовый MVP-проект на Python для цепочки: клиент → заявка → Airtable → поставщики → маршрут → накладная → бухгалтерия. Бот сделан на библиотеке `pyTelegramBotAPI` (`telebot`) и работает с вашими готовыми таблицами Airtable.

## Что умеет MVP

- Авторизация клиента по `access_code` из таблицы `Clients`.
- Привязка одного Telegram ID к одному клиенту.
- Создание заказа через кнопки: категория → товар → количество → время → комментарий → подтверждение.
- Создание заказа свободным текстом: например, `Нужны 10 молока и 3 сливок на завтра утром`.
- Сохранение заказа в `Orders` и позиций в `Order_Items`.
- Автоматическая группировка товаров по `supplier_id` и уведомление поставщиков в Telegram.
- Автоматический подбор водителя по району клиента и создание записи в `Routes`.
- Генерация HTML-накладной и запись ссылки в `Invoices`.
- Отправка маршрута водителю и накладной бухгалтеру.
- Базовый ИИ-ассистент: локальный парсер работает без OpenAI; при наличии `OPENAI_API_KEY` используется OpenAI.

## Структура проекта

```text
app/
  main.py                  # точка запуска бота
  config.py                # переменные окружения
  models.py                # статусы, DTO, черновик заказа
  bot/                     # обработчики Telegram и клавиатуры
  services/                # Airtable, бизнес-логика, ИИ, документы, уведомления
documents/invoices/        # локальные накладные
tests/                     # автотесты
.env.example               # пример настроек
requirements.txt           # зависимости
```

## Подготовка Airtable

Используйте ваши таблицы и поля без переименования:

- `Clients`
- `Products`
- `Suppliers`
- `Orders`
- `Order_Items`
- `Drivers`
- `Routes`
- `Invoices`

Важно:

1. В `Clients.access_code` должны быть уникальные коды, например `COFFEE001`.
2. В `Clients.status`, `Products.status`, `Suppliers.status`, `Drivers.status` активные записи должны иметь значение `active`.
3. В `Products.supplier_id` должна быть ссылка на поставщика из `Suppliers`.
4. В `Suppliers.telegram_id`, `Drivers.telegram_id` и настройке `ACCOUNTANT_TELEGRAM_IDS` должны быть реальные Telegram ID получателей.
5. Водитель выбирается по совпадению `Clients.district` с одним из значений multiple-select поля `Drivers.district`. Если совпадения нет, будет выбран первый активный водитель.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Настройка `.env`

Обязательные значения:

```env
TELEGRAM_BOT_TOKEN=токен_бота_от_BotFather
AIRTABLE_API_KEY=ваш_airtable_pat
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
ADMIN_TELEGRAM_IDS=111111111
ACCOUNTANT_TELEGRAM_IDS=333333333
MANAGER_CONTACT=@manager_username
```

Опционально:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
PUBLIC_BASE_URL=https://your-domain.kz
DOCUMENTS_DIR=documents
```

Если `PUBLIC_BASE_URL` пустой, бот сохранит в Airtable локальную `file://` ссылку на HTML-накладную. Для продакшена лучше настроить nginx/static hosting и указать публичный URL, чтобы водитель и бухгалтер могли открыть документ из Telegram.

## Запуск

```bash
python -m app.main
```

После запуска откройте Telegram-бота и отправьте `/start`.

## Как пользоваться клиенту

1. Клиент отправляет `/start`.
2. Бот просит код доступа.
3. Клиент вводит код из `Clients.access_code`, например `COFFEE001`.
4. Бот сохраняет `telegram_id` в таблицу `Clients`.
5. Клиент выбирает `🛒 Сделать заказ`.
6. Клиент выбирает категорию, товар, количество, интервал доставки и комментарий.
7. Клиент подтверждает заказ.
8. Бот создает записи в Airtable, формирует маршрут, накладную и отправляет уведомления.

Также можно написать текстом:

```text
Нужны 10 молока и 3 сливок на завтра утром
```

## Как добавить клиента

1. Откройте таблицу `Clients`.
2. Создайте строку.
3. Заполните `name`, `access_code`, `address`, `district`, `contact_person`, `phone`.
4. Убедитесь, что `status = active`.
5. Передайте клиенту код доступа.

## Как сбросить привязку Telegram ID

В MVP проще всего вручную открыть `Clients` и очистить поле `telegram_id`. После этого клиент сможет снова авторизоваться по своему `access_code`.

## Как добавить товар

1. Откройте `Products`.
2. Создайте строку.
3. Заполните `category`, `name`, `unit`, `supplier_id`, `purchase_price`, `sale_price`.
4. Установите `status = active`.

## Как добавить поставщика

1. Откройте `Suppliers`.
2. Создайте строку.
3. Заполните `name`, `telegram_id`, `phone`, `warehouse_address`.
4. Установите `status = active`.

## Как добавить водителя

1. Откройте `Drivers`.
2. Создайте строку.
3. Заполните `name`, `telegram_id`, `phone`, `district`.
4. Установите `status = active`.

## Резервное копирование

- Airtable: используйте экспорт CSV для каждой таблицы или Airtable snapshots.
- Код: храните проект в Git.
- Документы: регулярно копируйте папку `documents/invoices` на диск или в облако.

## Деплой на VPS

Пример systemd-сервиса:

```ini
[Unit]
Description=Food Supply Telegram Bot
After=network.target

[Service]
WorkingDirectory=/opt/food-supply-bot
EnvironmentFile=/opt/food-supply-bot/.env
ExecStart=/opt/food-supply-bot/.venv/bin/python -m app.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Команды:

```bash
sudo systemctl daemon-reload
sudo systemctl enable food-supply-bot
sudo systemctl start food-supply-bot
sudo systemctl status food-supply-bot
```

## Проверка проекта

```bash
pytest
python -m compileall app tests
```
