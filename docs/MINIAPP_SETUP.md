# Как поставить Mini App (Исповедь)

## Важно: визитка на GitHub Pages **не сломается**

Сайт `https://vaggo01.github.io` живёт в корне репозитория **`Vaggo01/Vaggo01.github.io`** (или pages из другого репо).

Бот **`Vaggo01/ispoved-bot`** — **другое** репо.  
Пока ты **не копируешь файлы бота поверх** `index.html` визитки — сайт цел.

### Безопасный вариант (рекомендую)

Положить Mini App в **подпапку** на Pages:

```
https://vaggo01.github.io/ispoved/
```

Как:
1. Открой репо визитки (тот, откуда крутится Pages).
2. Создай папку `ispoved/`.
3. Скопируй **содержимое** `app/dist/` из ispoved-bot:
   - `index.html`
   - `styles.css`
   - `app.js`
4. Commit + push визитки.
5. Проверь в браузере: `https://vaggo01.github.io/ispoved/`

Корень (`/`) не трогаем → Мия и визитка как были.

---

## Что ещё нужно (иначе Mini App «пустой»)

Mini App — это **фронт**. Данные идут на **API бота** (`/api/me`, `/api/qr`…).

### На Bothost

| Env | Пример |
|-----|--------|
| `BOT_TOKEN` | токен |
| `OWNERS` | `@vagdar1` |
| `DB_PATH` | путь на **постоянный диск**, напр. `/data/ispoved.db` |
| `API_PORT` | `8080` (или порт, который Bothost пробрасывает) |
| `API_HOST` | `0.0.0.0` |
| `API_CORS` | `https://vaggo01.github.io` или `*` |
| `WEBAPP_URL` | `https://vaggo01.github.io/ispoved/` |
| `SHEETS_URL` | пусто |

### BotFather

1. `@BotFather` → твой бот → **Bot Settings** → **Menu Button** / **Configure Mini App** / **Domain**
2. Domain: `vaggo01.github.io` (без `https://`)
3. Menu button URL: `https://vaggo01.github.io/ispoved/`

### Связка API (критично)

Pages отдаёт **только статику**. API должен быть на **публичном HTTPS** URL бота.

Если Bothost даёт URL вида `https://xxx.bothost.ru` или IP+HTTPS:

1. В `WEBAPP_URL` — ссылка на Pages (`.../ispoved/`)
2. В `index.html` Mini App добавь перед `app.js`:

```html
<script>window.ISPOVED_API = "https://ТВОЙ-ПУБЛИЧНЫЙ-API-БОТА";</script>
<script src="app.js"></script>
```

или открой/настрой:

```
https://vaggo01.github.io/ispoved/?api=https://ТВОЙ-API
```

Если Bothost **не** даёт HTTPS снаружи — Mini App с API **не взлетит** с Pages. Тогда:
- VPS + Caddy (Pattern A из DESIGN), или
- раздавать `/app/` **с того же HTTPS**, что и API (один домен).

---

## Быстрая проверка

1. `python bot.py` → в логе `HTTP API` и `Mini App URL`
2. Браузер: `https://API/api/health` → `{"ok": true}`
3. Telegram: открыть бота → кнопка **Карта** / menu → Mini App
4. QR → официант (роль staff) вкладка **Зал** → скан/ввод карты

---

## Откат на оригинал

Файл: `backups/bot.py.original-first-commit`  
Локально также: `C:\Users\d456p\ispoved-original-bot.py`
