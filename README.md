# Исповедь — карта лояльности (Telegram + Mini App)

Бот для лаундж-бара **«Исповедь»** (Пермь): бонусы, уровни, штампы «каждый 8-й кальян», QR, админка, Mini App в стиле All Stars.

Полное ТЗ: [`docs/DESIGN.md`](docs/DESIGN.md)

## Что умеет (v2 Working MVP)

| Роль | Возможности |
|------|-------------|
| **Гость** | Mini App: карта, штампы, бонусы, уровни, QR, меню, история, акции, профиль |
| **Официант** | Mini App «Зал»: скан QR / ввод карты → чек → провести; или в боте `482951 2400` |
| **Админ** | Статистика, гости, купоны, рассылка, CSV, бэкап БД, роли |

## Быстрый старт

```bash
# 1. Переменные окружения
set BOT_TOKEN=123:ABC...
set OWNERS=@your_login
set DB_PATH=/data/ispoved.db
set WEBAPP_URL=https://YOUR_HTTPS_HOST/app/
set API_PORT=8080
set API_CORS=*

# 2. Запуск
python bot.py
```

Проверка API: `http://HOST:8080/api/health`  
Mini App (локально): `http://HOST:8080/app/`

## Bothost (твой текущий хост)

1. **Постоянный диск** для базы: `DB_PATH=/data/ispoved.db` (или путь Bothost volume).
2. Залей репозиторий целиком (`bot.py`, `web_api.py`, `app/dist/`).
3. Команда запуска: `python bot.py`
4. Если Bothost **не даёт публичный HTTPS** на порт API:
   - **Вариант A (лучше):** VPS с Caddy → TLS на домен, proxy `/api` и `/app` на `127.0.0.1:8080`
   - **Вариант B:** static Mini App на **GitHub Pages** (`app/dist`), API на Bothost если есть public URL; в `app.js` можно `?api=https://api.example.com`
5. В @BotFather → Bot Settings → **Domain** = домен Mini App (без `https://`).
6. `WEBAPP_URL=https://твой-домен/app/` (или Pages URL).

> «Сервера Grok» для чужого бара **не используем**: нет SLA, нет твоего контроля, риск для оплаты. Bothost + volume + HTTPS static — надёжный путь.

## Переменные

| Env | Default | Смысл |
|-----|---------|--------|
| `BOT_TOKEN` | — | токен BotFather |
| `OWNERS` | — | `@user` владельца |
| `DB_PATH` | `ispoved.db` | файл SQLite (ставь на volume!) |
| `WEBAPP_URL` | `""` | HTTPS URL Mini App |
| `API_HOST` | `0.0.0.0` | bind HTTP |
| `API_PORT` | `8080` | `0` = без HTTP |
| `API_CORS` | `*` | CORS origin |
| `SHEETS_URL` | `""` | Apps Script (пусто = выкл) |
| `BACKUP_ENABLED` | `1` | ежедневный .db в TG админам |

## Google Таблица

По умолчанию **выключена** (раньше URL был захардкожен и «висела» мёртвой).  
Нужна — положи рабочий Apps Script в `SHEETS_URL`. Иначе: **CSV из админки** + **бэкап .db в личку**.

## QR: как считывать

1. Гость: Mini App → иконка QR → крупный код (в коде — **6 цифр** карты).
2. Официант: вкладка **Зал** → **Сканировать** (мобильный Telegram) или ввод номера.
3. Deep-link: `https://t.me/Ispovedloalbot?start=c482951`

## Тесты

```bash
python -m unittest discover -s tests -v
```

## Структура

```
bot.py          # ядро, long-poll, DB, checkout
web_api.py      # HTTP API + static
app/dist/       # Mini App (HTML/CSS/JS)
docs/DESIGN.md  # полное ТЗ
tests/          # unittest
```

## Сдать заказчику — чеклист

- [ ] `DB_PATH` на постоянном диске  
- [ ] Бэкап .db приходит админу  
- [ ] Mini App открывается в Telegram  
- [ ] QR → официант находит гостя  
- [ ] Чек начисляет бонусы, двойной тап не дублирует  
- [ ] Меню и профиль в Mini App  
- [ ] `SHEETS` не врёт «подключена», если пусто  
