# Регистрация на турнир: Telegram Mini App

## 1. Google
1. Google Cloud → включить Google Sheets API → создать сервисный аккаунт → ключ JSON → сохранить как `service_account.json` рядом с `main.py`.
2. Создать Google Таблицу, нажать «Поделиться» и дать доступ редактора на email сервисного аккаунта.
3. ID таблицы — часть ссылки между `/d/` и `/edit`.

## 2. Настройка
Скопируйте `.env.example` в `.env` и заполните. `ADMIN_CHAT_ID` — по желанию (ваш Telegram ID, придёт уведомление о каждой команде).

## 3. Запуск
    pip install -r requirements.txt
    uvicorn main:app --port 8000

## 4. HTTPS и кнопка в боте
Нужен публичный HTTPS-адрес (тест: `cloudflared tunnel --url http://localhost:8000`).
Впишите его в `WEBAPP_URL` и выполните один раз:

    python setup_bot.py

## 5. Деплой (Render / Railway / VPS)
Dockerfile уже есть. Задайте переменные из `.env` в настройках сервиса, `service_account.json` загрузите как secret file.
Хранилище JSON на бесплатных хостингах может сбрасываться при перезапуске, основная копия данных в Google Таблице.

## Админка
`https://ваш-домен/admin?token=ADMIN_TOKEN`: список команд и ссылка на `teams.json`.
