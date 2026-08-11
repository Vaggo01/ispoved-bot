# -*- coding: utf-8 -*-
"""
Бот «Исповедь» — карта лояльности лаундж-бара.
Пермь, ул. Николая Островского, 93Д.

Весь бот в одном файле. Сторонних библиотек нет —
только стандартная библиотека Python.

Запуск:  python3 bot.py
"""
import os
import zlib
import struct
import sqlite3
import threading
import time
import datetime
import random
import string
import json
import shutil
import re
import traceback
import os, sys, tempfile, shutil, urllib.request, urllib.parse, urllib.error

# После склейки все модули — это один и тот же файл. Некоторые
# функции принимают модуль параметром (например, send_to_admins(tg, ...)),
# поэтому имена должны существовать и указывать сами на себя.
tg = db = config = backup = qr = sys.modules[__name__]

# ══════════════════════════════════════════════════════════════
#  МЕНЮ ЗАВЕДЕНИЯ — правится здесь
# ══════════════════════════════════════════════════════════════
# Показывается гостю в разделе «Меню».
# t — название, d — описание, p — цена в рублях, tag — метка.
MENU = [
    {"id": 'hookah', "t": 'Кальяны', "items": [
        {"id": 'hoo1', "t": 'Кальян классика', "p": 1300},
        {"id": 'hoo2', "t": 'Кальян премиум', "p": 1500},
        {"id": 'hoo3', "t": 'Фруктовая чаша', "p": 2000},
        {"id": 'hoo4', "t": 'Кальян парфюм', "p": 2000},
        {"id": 'hoo5', "t": 'Ланч-кальян', "d": 'с 12:00 до 16:00 при покупке кальяна классический чай в подарок', "p": 1300},
        {"id": 'hoo6', "t": '"Второе дыхание"', "d": 'Закажи сразу 2 классических кальяна со скидкой', "p": 2200},
    ]},
    {"id": 'pizza', "t": 'Пицца 30 см', "items": [
        {"id": 'piz1', "t": 'Жюльен', "d": 'Сливочно-грибной соус, нежное куриное филе, лук, шампиньоны, опята, сыр Моцарелла', "p": 850},
        {"id": 'piz2', "t": 'Барбекю', "d": 'Рваная свинина, копченая курица, корнишоны, сыр Моцарелла, карамелизированный лук, соус барбекю', "p": 850},
        {"id": 'piz3', "t": '4 сыра', "d": 'Сыр cream cheese, сыр дорблю, сыр "Моцарелла" тёртый, сыр Гауда', "p": 850},
        {"id": 'piz4', "t": 'С чоризо и беконом', "d": 'Соус томатный, колбаски чоризо, бекон, болгарский перец, лук красный, сыр "Моцарелла" тёртый', "p": 850},
        {"id": 'piz5', "t": 'Мясная с опятами', "d": 'Соус томатный, соус сальса, сыр "Моцарелла" тёртый, копченая курица, баварские колбаски, опята маринованные, корнишоны', "p": 850},
        {"id": 'piz6', "t": 'Дьябло', "d": 'Соус томатный, соус барбекю, сыр "Моцарелла" тёртый, корнишоны, перец халапеньо, колбаса пепперони', "p": 850},
        {"id": 'piz7', "t": 'Груша-дорблю', "d": 'Соус сливочно-сырный, сыр дорблю, груша, мед, грецкий орех, сыр "Моцарелла" тёртый', "p": 850},
        {"id": 'piz8', "t": 'Чикен-рэнч', "d": 'Чесночный соус рэнч, соус томатный, копченая куриная грудка, ветчина куриная, сыр "Моцарелла" тёртый', "p": 850},
        {"id": 'piz9', "t": 'Половина пицца', "d": 'любая пицца', "p": 500},
    ]},
    {"id": 'tea', "t": 'Чай', "items": [
        {"id": 'tea1', "t": 'Классический чай', "d": '1 литр', "p": 300},
        {"id": 'tea2', "t": 'Зеленый', "d": '1 л', "p": 300},
        {"id": 'tea3', "t": 'Черный', "d": '1 л', "p": 300},
        {"id": 'tea4', "t": 'Черный с бергамотом', "d": '1 л', "p": 300},
        {"id": 'tea5', "t": 'Черный с чабрецом', "d": '1 л', "p": 300},
        {"id": 'tea6', "t": 'Красный', "d": '1 л', "p": 300},
        {"id": 'tea7', "t": 'Травяной сбор', "d": '1 л', "p": 450},
        {"id": 'tea8', "t": 'Авторский чай', "d": '1 л', "p": 600},
        {"id": 'tea9', "t": 'Облепиховый', "d": 'облепиха, апельсин, лимон, корица, черный чай', "p": 600},
        {"id": 'tea10', "t": 'Цитрусовый', "d": 'апельсин, лимон, лайм, зелёный чай', "p": 600},
        {"id": 'tea11', "t": 'Вишневый', "d": 'Черешня/вишня, лимон, мята, красный чай', "p": 600},
        {"id": 'tea12', "t": 'Фруктовый', "d": 'Груша, яблоко, мята, зеленый чай', "p": 600},
        {"id": 'tea13', "t": 'Пряный', "d": 'Яблоко, апельсин, лимон, корица, бадьян, гвоздика, мёд, красный чай', "p": 600},
    ]},
    {"id": 'coffee', "t": 'Кофе', "items": [
        {"id": 'cof1', "t": 'Латте', "p": 260},
        {"id": 'cof2', "t": 'Капучино', "p": 260},
        {"id": 'cof3', "t": 'Американо', "p": 160},
        {"id": 'cof4', "t": 'Эспрессо', "p": 100},
        {"id": 'cof5', "t": 'Матча-латте', "p": 300},
    ]},
    {"id": 'lemonade', "t": 'Авторские лимонады', "items": [
        {"id": 'lem1', "t": 'Ягодный', "d": 'Мята, сироп черная смородина, сироп гренадин, клюквенный сок', "p": 600},
        {"id": 'lem2', "t": 'Тропический', "d": 'Мята, сироп маракуя, ананасовый сок', "p": 600},
        {"id": 'lem3', "t": 'Фруктовый', "d": 'Мята, сироп зелёное яблоко, грушевый сок', "p": 600},
        {"id": 'lem4', "t": 'Цитрусовый', "d": 'Мята, сироп блю-кюрасао, сироп грейпфрут, апельсиновый сок', "p": 600},
    ]},
    {"id": 'soda', "t": 'Газированные напитки', "items": [
        {"id": 'sod1', "t": 'Кола', "d": '0.33', "p": 250},
        {"id": 'sod2', "t": 'Фанта', "d": '0.33', "p": 250},
        {"id": 'sod3', "t": 'Спрайт', "d": '0.33', "p": 250},
        {"id": 'sod4', "t": 'Ред булл', "d": '0.35', "p": 300},
        {"id": 'sod5', "t": 'Вода газ/негаз', "d": '0.5', "p": 250},
    ]},
    {"id": 'dessert', "t": 'Десерты', "items": [
        {"id": 'des1', "t": 'Чизкейк', "d": 'в ассортименте', "p": 300},
        {"id": 'des2', "t": 'Топинг', "d": 'Шоколад/ карамель/ клубника/ фисташка', "p": 30},
    ]},
    {"id": 'cocktails', "t": 'Классические коктейли', "alco": True, "items": [
        {"id": 'coc1', "t": 'Дайкири', "d": 'Лайм, ром, сироп сахар', "p": 480},
        {"id": 'coc2', "t": 'Негрони', "d": 'Кампари, джин, красный вермут', "p": 500},
        {"id": 'coc3', "t": 'Лонгайленд', "d": 'Водка, джин, ликер апельсин, ром, текила, кола, лимон', "p": 550},
        {"id": 'coc4', "t": 'Мохито', "d": 'Лайм, ром, сироп сахар, содовая, мята', "p": 500},
        {"id": 'coc5', "t": 'Апероль спритц', "d": 'Апероль, содовая, игристое вино, сироп сахар', "p": 550},
    ]},
    {"id": 'author', "t": 'Авторские коктейли', "alco": True, "items": [
        {"id": 'aut1', "t": 'Гордыня', "d": 'Бурбон, вишневый ликер, ореховый сироп, содовая', "p": 520},
        {"id": 'aut2', "t": 'Алчность', "d": 'Белый вермут, игристое вино, пюре персик, сок лимона', "p": 520},
        {"id": 'aut3', "t": 'Гнев', "d": 'Грейпфрутовый сок, табаско, водка, вишневый ликер, сироп малина, сок лимона', "p": 520},
        {"id": 'aut4', "t": 'Похоть', "d": 'Текила, игристое вино, сироп клюква, сок лимона, сироп черная смородина', "p": 520},
        {"id": 'aut5', "t": 'Ленность', "d": 'Лимончелла, ликер дыня, сок лимона, белок', "p": 520},
        {"id": 'aut6', "t": 'Скромность', "d": 'Джин, мята, березовый сок, сок лимона, сахарный сироп', "p": 520},
        {"id": 'aut7', "t": 'Щедрость', "d": 'Абсент, яблочный сок, ликер дыня, сок лимона, содовая', "p": 520},
        {"id": 'aut8', "t": 'Спокойствие', "d": 'Джин, сироп базилик, сок лимона, белок', "p": 520},
        {"id": 'aut9', "t": 'Целомудрие', "d": 'Красное вино, вермут, сироп клюква, сок лимона', "p": 520},
        {"id": 'aut10', "t": 'Бодрость', "d": 'Апельсиновый сок, кофейный ликер, водка, сок лимона, сироп карамель', "p": 520},
    ]},
    {"id": 'strong', "t": 'Крепкий алкоголь', "alco": True, "items": [
        {"id": 'str1', "t": 'Водка "Organic"', "d": '0.4', "p": 250},
        {"id": 'str2', "t": 'Виски зерновой (Бурбон) "Jim Beam"', "d": '0.4', "p": 350},
        {"id": 'str3', "t": 'Ликер десертный "Jägermeister"', "d": '0.35', "p": 320},
        {"id": 'str4', "t": 'Ром выдержанный "Barcelo Blanco"', "d": '0.375', "p": 280},
        {"id": 'str5', "t": 'Текила "La Pavesa" Plata', "d": '0.4', "p": 280},
        {"id": 'str6', "t": 'Виски купаж. 3 г.в. "Nucky Thompson"', "d": '0.4', "p": 280},
    ]},
    {"id": 'wine', "t": 'Вино', "alco": True, "items": [
        {"id": 'win1', "t": '"Gaetano" Pinot Grigio Terre degli Osci', "d": 'Сортовое, ординарное, сухое белое, 10%', "p": 350},
        {"id": 'win2', "t": '"Vale d\'Este" Rose Vinho Verde', "d": 'Ординарное, полусухое розовое, 10%', "p": 350},
        {"id": 'win3', "t": '"Peter Weinbach" Riesling Medium Dry', "d": 'Сортовое, полусухое белое, 11,5%', "p": 350},
    ]},
    {"id": 'vermouth', "t": 'Вермут', "alco": True, "items": [
        {"id": 'ver1', "t": 'Martini "Bianco"', "d": '0.15', "p": 370},
        {"id": 'ver2', "t": 'Martini "Roso"', "d": '0.15', "p": 370},
    ]},
    {"id": 'beer', "t": 'Пиво и сидр', "alco": True, "items": [
        {"id": 'bee1', "t": 'Люгер 0,5', "d": 'Светлое нефильтрованное. 4,7%', "p": 350},
        {"id": 'bee2', "t": 'Флюгер 0,5', "d": 'Светлое фильтрованное. 4,7%', "p": 350},
        {"id": 'bee3', "t": 'Bergauer 0,5', "d": 'безалко, Светлое фильтрованное. 0,0 %', "p": 350},
        {"id": 'bee4', "t": 'Blanche de croix', "d": 'Светлое нефильтрованное. 5%', "p": 350},
        {"id": 'bee5', "t": 'Баварский Вайцен 0,5', "d": 'Вайцен (Пшеничное) 5%', "p": 350},
        {"id": 'bee6', "t": 'Баварский Дункель 0,5', "d": 'Темное 5%', "p": 350},
        {"id": 'bee7', "t": 'Хмельной мёд Традиционный', "d": 'Медовуха, 5,7%', "p": 350},
        {"id": 'bee8', "t": 'Хмельной мёд Яблочный сидр', "d": 'Полусладкое, фильтрованное, 4,9%', "p": 350},
        {"id": 'bee9', "t": 'Cherie Cherry 0,45', "d": 'Вкус: вишня. Нефильтрованное осветленное', "p": 450},
        {"id": 'bee10', "t": 'Mon Cher Cassis 0,45', "d": 'Вкус: черная смородина. Нефильтрованное осветленное', "p": 450},
        {"id": 'bee11', "t": 'Ma Chere Framboise, 0,45', "d": 'Вкус: малина. Нефильтрованное, осветленное', "p": 450},
    ]},
    {"id": 'shots', "t": 'Шоты', "alco": True, "items": [
        {"id": 'sho1', "t": 'Ривьера', "d": 'сироп гренадин, ликер личи, текила', "p": 380},
        {"id": 'sho2', "t": 'Абсентерия', "d": 'сироп яблоко, самбука, игристое вино', "p": 380},
        {"id": 'sho3', "t": 'Рубиновый', "d": 'сироп грейпфрут, апероль, джин', "p": 380},
        {"id": 'sho4', "t": 'Лимонета', "d": 'Сироп смородина, ликер апельсин, лимончелло', "p": 380},
        {"id": 'sho5', "t": 'Ремалин', "d": 'Сироп малина, егерьмейстер, виски', "p": 380},
        {"id": 'sho6', "t": 'Набор из 5 шотов с 10% скидкой', "d": '40 мл', "p": 380},
    ]},
]

# ══════════════════════════════════════════════════════════════
#  НАСТРОЙКИ — правится только этот раздел
# ══════════════════════════════════════════════════════════════
"""
НАСТРОЙКИ БОТА «Исповедь»
Правится только этот файл. Остальной код трогать не нужно.
"""

# ── Токен бота ────────────────────────────────────────────────
# 1) env: BOT_TOKEN / TELEGRAM_BOT_TOKEN / API_TOKEN
# 2) файл (обход глюка Bothost env): /app/data/bot_token.txt или bot_token.txt
def _load_token():
    for key in ("BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "API_TOKEN"):
        v = (os.environ.get(key) or "").strip()
        if v and "ВСТАВЬ" not in v:
            return v
    for path in (
        os.path.join("/app/data", "bot_token.txt"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_token.txt"),
        "bot_token.txt",
    ):
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    v = f.read().strip().splitlines()[0].strip()
                if v and not v.startswith("#"):
                    return v
        except Exception:
            pass
    return "ВСТАВЬ_СЮДА_ТОКЕН"

TOKEN = _load_token()

# ── Кто есть кто ──────────────────────────────────────────────
# Здесь задаётся ТОЛЬКО первый владелец — чтобы было кому раздать
# остальные роли. Дальше всё делается кнопками в боте, раздел «Роли».
#
# Можно указать @логин или числовой ID, через запятую — несколько.
# Роли хранятся в базе, поэтому этот список применяется один раз,
# при самом первом запуске на пустой базе. Снятую в боте роль
# он обратно не вернёт.
OWNERS = [x.strip() for x in os.environ.get("OWNERS", "@posutivkusna,@vagdar1").split(",") if x.strip()]

# Устаревшие списки. Оставлены для совместимости: если они заданы,
# люди из них тоже попадут в базу при первом запуске.
ADMINS = [x.strip() for x in os.environ.get("ADMINS", "").split(",") if x.strip()]
STAFF  = [x.strip() for x in os.environ.get("STAFF",  "").split(",") if x.strip()]

# ── Заведение ─────────────────────────────────────────────────
BRAND = {
    "name":  "Исповедь",
    "kind":  "лаундж-бар",
    "city":  "Пермь",
    "addr":  "ул. Николая Островского, 93Д",
    "phone": "+7 (342) 000-00-00",
    "hours": "вс–чт 14:00–02:00 · пт–сб 14:00–04:00",
}

# ── Правила лояльности ────────────────────────────────────────
LOYALTY = {
    "cashback":        5,     # % кэшбэка с чека (базовый уровень)
    "max_pay_percent": 30,    # максимум % чека, оплачиваемый бонусами
    "welcome":         300,   # бонусов при регистрации
    "second_visit":    500,   # бонусов на второй визит
    "birthday":        1000,  # бонусов в день рождения
    "burn_days":       180,   # сгорание бонусов без визитов (0 = не сгорают)
    "levels": [               # уровни по сумме всех чеков
        {"name": "Гость",    "from": 0,     "cashback": 5},
        {"name": "Свой",     "from": 15000, "cashback": 7},
        {"name": "Резидент", "from": 50000, "cashback": 10},
    ],
}

# ── Google Таблица ────────────────────────────────────────────
# Live-sync выключен по умолчанию (раньше был hardcoded URL — «подключена»
# без реального Apps Script). Задайте SHEETS_URL в env, если скрипт есть.
# Пустая строка = выгрузка выключена, бот работает как обычно.
SHEETS_URL = os.environ.get("SHEETS_URL", "").strip()

# ── Ссылка на мини-приложение ─────────────────────────────────
# HTTPS URL Mini App.
# ispoved-perm → https://ispoved-perm.bothost.tech/app/
# ispoved-perm.bothost.tech → https://ispoved-perm.bothost.tech/app/
def _norm_webapp_url(raw):
    u = (raw or "").strip()
    if not u:
        return ""
    # убрать случайный полный URL с пробелами
    u = u.replace(" ", "")
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u.lstrip("/")
    parsed = urllib.parse.urlparse(u)
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    # если host пуст (кривой URL) — не используем
    if not host:
        return ""
    # короткое имя без точки: ispoved-perm → ispoved-perm.bothost.tech
    if "." not in host:
        host = host + ".bothost.tech"
    # path пустой или / → /app/
    if not path or path == "/":
        path = "/app"
    path = path.rstrip("/") + "/"
    return "https://{0}{1}".format(host, path)

# Bothost: WEBAPP_URL или DOMAIN (часто без https)
WEBAPP_URL = _norm_webapp_url(
    os.environ.get("WEBAPP_URL")
    or os.environ.get("DOMAIN")
    or ""
)

# ── HTTP API для Mini App (stdlib ThreadingHTTPServer) ────────
# Bothost: PORT из панели (прокси) ВАЖНЕЕ, чем API_PORT в env.
# Иначе домен даёт 404/502, а бот слушает «не тот» порт.
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
_port_raw = os.environ.get("PORT") or os.environ.get("API_PORT") or "8080"
try:
    API_PORT = int(_port_raw)
except ValueError:
    API_PORT = 8080
# CORS: origin Mini App (https://vaggo01.github.io) или * для отладки
API_CORS = os.environ.get("API_CORS", "*")

# ── Резервные копии базы ──────────────────────────────────────
# Раз в сутки бот присылает админам файл базы в личку.
# Если хостинг сотрёт данные при пересборке — пересылаете файл боту обратно.
# На хостингах без постоянного диска выключать НЕЛЬЗЯ.
BACKUP_ENABLED = os.environ.get("BACKUP_ENABLED", "1") != "0"
BACKUP_HOUR    = int(os.environ.get("BACKUP_HOUR", "5"))   # час по времени Перми

# ── Прочее ────────────────────────────────────────────────────
# Bothost: БД только в /app/data (volume). Иначе — локальный файл.
def _default_db_path():
    if os.environ.get("DB_PATH"):
        return os.environ["DB_PATH"]
    bothost_data = "/app/data"
    if os.path.isdir(bothost_data):
        try:
            os.makedirs(bothost_data, exist_ok=True)
        except OSError:
            pass
        return os.path.join(bothost_data, "ispoved.db")
    return "ispoved.db"

DB_PATH   = _default_db_path()
TIMEZONE  = 5          # UTC+5, Пермь
LOG_FILE  = "bot.log"


# ══════════════════════════════════════════════════════════════
#  ГЕНЕРАТОР QR-КОДА
# ══════════════════════════════════════════════════════════════
"""
Генератор QR-кода и картинки PNG — без единой сторонней библиотеки.

Зачем свой: Pillow и qrcode на хостинге пришлось бы ставить, а бот
задуман без зависимостей. PNG собираем вручную — формат позволяет,
если не жадничать со сжатием.

Поддержка: версии 1–6, коррекция M, режимы числовой / алфавитно-цифровой
/ байтовый UTF-8. Этого хватает на номер карты и короткую ссылку.
"""

# ── арифметика Галуа GF(256) для кодов Рида — Соломона ────────
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def _gmul(a, b):
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


def _rs_poly(n):
    """Порождающий многочлен для n проверочных байтов."""
    p = [1]
    for i in range(n):
        q = p + [0]
        for j in range(len(p)):
            q[j + 1] ^= _gmul(p[j], EXP[i])
        p = q
    return p


def _rs_encode(data, n):
    gen = _rs_poly(n)
    res = list(data) + [0] * n
    for i in range(len(data)):
        c = res[i]
        if c:
            for j in range(1, len(gen)):
                res[i + j] ^= _gmul(gen[j], c)
    return res[len(data):]


# размер, байт данных, байт коррекции, блоков — уровень M
VERSIONS = {
    1:  dict(size=21, data=16,  ecc=10, blocks=1),
    2:  dict(size=25, data=28,  ecc=16, blocks=1),
    3:  dict(size=29, data=44,  ecc=26, blocks=1),
    4:  dict(size=33, data=64,  ecc=18, blocks=2),
    5:  dict(size=37, data=86,  ecc=24, blocks=2),
    6:  dict(size=41, data=108, ecc=16, blocks=4),
    7:  dict(size=45, data=124, ecc=18, blocks=4),
    8:  dict(size=49, data=154, ecc=22, blocks=4),
    9:  dict(size=53, data=182, ecc=22, blocks=5),
    10: dict(size=57, data=216, ecc=26, blocks=5),
}

ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"

# Положение выравнивающих узоров по версиям.
ALIGN = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
    7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
}


class _Bits:
    def __init__(self):
        self.a = []

    def put(self, val, length):
        for i in range(length - 1, -1, -1):
            self.a.append((val >> i) & 1)

    def __len__(self):
        return len(self.a)


def _encode_data(text):
    """Уложить текст в поток бит и подобрать версию."""
    if text.isdigit():
        mode, cci_bits = 1, [10, 12]
    elif all(ch in ALNUM for ch in text):
        mode, cci_bits = 2, [9, 11]
    else:
        mode, cci_bits = 4, [8, 16]

    raw = text.encode("utf-8") if mode == 4 else None
    count = len(raw) if mode == 4 else len(text)

    for ver in sorted(VERSIONS):
        p = VERSIONS[ver]
        cci = cci_bits[0] if ver <= 9 else cci_bits[1]
        b = _Bits()
        b.put(mode, 4)
        b.put(count, cci)

        if mode == 1:
            i = 0
            while i + 2 < len(text):
                b.put(int(text[i:i + 3]), 10)
                i += 3
            rest = len(text) - i
            if rest == 2:
                b.put(int(text[i:i + 2]), 7)
            elif rest == 1:
                b.put(int(text[i]), 4)
        elif mode == 2:
            i = 0
            while i + 1 < len(text):
                b.put(ALNUM.index(text[i]) * 45 + ALNUM.index(text[i + 1]), 11)
                i += 2
            if i < len(text):
                b.put(ALNUM.index(text[i]), 6)
        else:
            for byte in raw:
                b.put(byte, 8)

        capacity = p["data"] * 8
        if len(b) > capacity:
            continue

        # завершитель и выравнивание до целых байт
        for _ in range(min(4, capacity - len(b))):
            b.a.append(0)
        while len(b) % 8:
            b.a.append(0)

        data = bytearray()
        for i in range(0, len(b), 8):
            data.append(int("".join(map(str, b.a[i:i + 8])), 2))
        pad = [0xEC, 0x11]
        k = 0
        while len(data) < p["data"]:
            data.append(pad[k % 2])
            k += 1

        # разбиение на блоки и чередование
        nb = p["blocks"]
        per = len(data) // nb
        blocks, eccs = [], []
        off = 0
        for i in range(nb):
            n = per + (1 if i >= nb - (len(data) - per * nb) else 0)
            blk = list(data[off:off + n])
            off += n
            blocks.append(blk)
            eccs.append(_rs_encode(blk, p["ecc"]))

        out = []
        for i in range(max(len(x) for x in blocks)):
            for blk in blocks:
                if i < len(blk):
                    out.append(blk[i])
        for i in range(p["ecc"]):
            for e in eccs:
                out.append(e[i])
        return out, ver
    raise ValueError("Текст слишком длинный для QR версии 6")


def build(text):
    """Матрица QR: список списков 0/1."""
    codewords, ver = _encode_data(text)
    p = VERSIONS[ver]
    n = p["size"]
    m = [[None] * n for _ in range(n)]

    def finder(r, c):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                rr, cc = r + dr, c + dc
                if not (0 <= rr < n and 0 <= cc < n):
                    continue
                inside = 0 <= dr <= 6 and 0 <= dc <= 6
                if inside:
                    edge = dr in (0, 6) or dc in (0, 6)
                    core = 2 <= dr <= 4 and 2 <= dc <= 4
                    m[rr][cc] = 1 if (edge or core) else 0
                else:
                    m[rr][cc] = 0

    finder(0, 0)
    finder(0, n - 7)
    finder(n - 7, 0)

    # синхрополосы
    for i in range(8, n - 8):
        v = 1 if i % 2 == 0 else 0
        if m[6][i] is None:
            m[6][i] = v
        if m[i][6] is None:
            m[i][6] = v

    # выравнивающие узоры
    pos = ALIGN.get(ver, [])
    for r in pos:
        for c in pos:
            if (r < 8 and c < 8) or (r < 8 and c > n - 9) or (r > n - 9 and c < 8):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    m[r + dr][c + dc] = 1 if (max(abs(dr), abs(dc)) != 1) else 0

    # места под формат
    for i in range(9):
        if m[8][i] is None:
            m[8][i] = 0
        if m[i][8] is None:
            m[i][8] = 0
    for i in range(8):
        if m[8][n - 1 - i] is None:
            m[8][n - 1 - i] = 0
        if m[n - 1 - i][8] is None:
            m[n - 1 - i][8] = 0
    m[n - 8][8] = 1          # всегда тёмный модуль

    # укладка данных змейкой снизу вверх
    bits = []
    for cw in codewords:
        for i in range(7, -1, -1):
            bits.append((cw >> i) & 1)

    idx = 0
    col = n - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(n - 1, -1, -1) if upward else range(n)
        for row in rows:
            for c in (col, col - 1):
                if m[row][c] is None:
                    bit = bits[idx] if idx < len(bits) else 0
                    idx += 1
                    # маска 0: (row + col) % 2 == 0
                    if (row + c) % 2 == 0:
                        bit ^= 1
                    m[row][c] = bit
        upward = not upward
        col -= 2

    # биты формата: уровень M (00) + маска 000
    fmt = 0b00 << 3 | 0
    rem = fmt << 10
    for _ in range(5):
        if rem >> (14 - (14 - rem.bit_length() + 1)) if False else False:
            pass
    # деление на порождающий 0b10100110111
    v = fmt << 10
    g = 0b10100110111
    while v.bit_length() >= 11:
        v ^= g << (v.bit_length() - 11)
    fmt_bits = ((fmt << 10) | v) ^ 0b101010000010010

    for i in range(15):
        bit = (fmt_bits >> i) & 1
        if i < 6:
            m[8][i] = bit
        elif i == 6:
            m[8][7] = bit
        elif i == 7:
            m[8][8] = bit
        elif i == 8:
            m[7][8] = bit
        else:
            m[14 - i][8] = bit
        if i < 8:
            m[n - 1 - i][8] = bit
        else:
            m[8][n - 15 + i] = bit
    m[n - 8][8] = 1

    return [[cell or 0 for cell in row] for row in m]


def png(text, scale=8, quiet=4, dark=(0, 0, 0), light=(255, 255, 255)):
    """QR как PNG в виде bytes. Собираем формат вручную, без Pillow."""
    m = build(text)
    n = len(m)
    size = (n + quiet * 2) * scale

    # строки изображения: каждая начинается с байта фильтра 0
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        my = y // scale - quiet
        for x in range(size):
            mx = x // scale - quiet
            on = (0 <= my < n and 0 <= mx < n and m[my][mx])
            rows.extend(dark if on else light)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)   # 8 бит, RGB
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + chunk(b"IEND", b""))


# ══════════════════════════════════════════════════════════════
#  БАЗА ДАННЫХ
# ══════════════════════════════════════════════════════════════
"""База данных: гости, визиты, купоны, рассылки, очередь в Google Таблицу."""

_lock = threading.RLock()
_conn = None

def conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        init()
    return _conn

def close():
    """Закрыть соединение с базой (нужно при восстановлении из копии)."""
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None

def init():
    with _lock:
        c = _conn
        c.executescript("""
        CREATE TABLE IF NOT EXISTS guests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id      INTEGER UNIQUE,
            card       TEXT UNIQUE,
            name       TEXT DEFAULT '',
            username   TEXT DEFAULT '',
            phone      TEXT DEFAULT '',
            bday       TEXT DEFAULT '',
            bonus      INTEGER DEFAULT 0,
            spent      INTEGER DEFAULT 0,
            visits     INTEGER DEFAULT 0,
            created    TEXT,
            last_visit TEXT,
            note       TEXT DEFAULT '',
            blocked    INTEGER DEFAULT 0,
            got_second INTEGER DEFAULT 0,
            got_bday   TEXT DEFAULT '',
            muted      INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS visits(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id   INTEGER,
            type       TEXT,
            total      INTEGER DEFAULT 0,
            paid_pts   INTEGER DEFAULT 0,
            paid_money INTEGER DEFAULT 0,
            earned     INTEGER DEFAULT 0,
            extra_why  TEXT DEFAULT '',
            items      TEXT DEFAULT '',
            at         TEXT,
            by_user    TEXT DEFAULT '',
            FOREIGN KEY(guest_id) REFERENCES guests(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS coupons(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code       TEXT UNIQUE,
            title      TEXT,
            kind       TEXT,            -- points | percent | gift
            value      INTEGER DEFAULT 0,
            min_check  INTEGER DEFAULT 0,
            uses_left  INTEGER DEFAULT 1,
            per_guest  INTEGER DEFAULT 1,
            until      TEXT DEFAULT '',
            created    TEXT,
            active     INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS coupon_uses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_id INTEGER, guest_id INTEGER, at TEXT,
            FOREIGN KEY(coupon_id) REFERENCES coupons(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS sheet_queue(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT, tries INTEGER DEFAULT 0, at TEXT
        );
        CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
        CREATE TABLE IF NOT EXISTS roles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id    INTEGER DEFAULT 0,     -- 0, пока человек не написал боту
            username TEXT DEFAULT '',       -- без @, в нижнем регистре
            role     TEXT,                  -- owner | admin | staff
            note     TEXT DEFAULT '',
            added_by TEXT DEFAULT '',
            at       TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ix_roles_user ON roles(username) WHERE username<>'';
        CREATE INDEX IF NOT EXISTS ix_roles_tg ON roles(tg_id);
        CREATE INDEX IF NOT EXISTS ix_visits_guest ON visits(guest_id);
        CREATE INDEX IF NOT EXISTS ix_visits_at    ON visits(at);
        CREATE INDEX IF NOT EXISTS ix_guests_card  ON guests(card);
        CREATE TABLE IF NOT EXISTS schema_migrations(
            id TEXT PRIMARY KEY,
            applied_at TEXT
        );
        CREATE TABLE IF NOT EXISTS dialog_state(
            tg_id INTEGER PRIMARY KEY,
            mode TEXT DEFAULT '',
            data_json TEXT DEFAULT '{}',
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS idempotency_keys(
            key TEXT PRIMARY KEY,
            request_hash TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        c.commit()
        _run_migrations(c)


def _run_migrations(c):
    """Additive migrations. Safe to re-run. Backup recommended before deploy."""
    applied = {r[0] for r in c.execute("SELECT id FROM schema_migrations").fetchall()}
    # Future SQL files can land here; baseline tables already created above.
    for mid, sql in (
        ("002_guest_profile_fields",
         "ALTER TABLE guests ADD COLUMN last_name TEXT DEFAULT '';"
         "ALTER TABLE guests ADD COLUMN gender TEXT DEFAULT '';"
         "ALTER TABLE guests ADD COLUMN sopd_at TEXT DEFAULT '';"
         "ALTER TABLE guests ADD COLUMN stamp_count INTEGER DEFAULT 0;"
         "ALTER TABLE guests ADD COLUMN free_hookah_pending INTEGER DEFAULT 0;"
         "ALTER TABLE guests ADD COLUMN profile_complete INTEGER DEFAULT 0;"),
    ):
        if mid in applied:
            continue
        try:
            # SQLite: ADD COLUMN fails if exists — ignore duplicates on re-deploy
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                try:
                    c.execute(stmt)
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        raise
            c.execute(
                "INSERT OR IGNORE INTO schema_migrations(id, applied_at) VALUES(?,?)",
                (mid, now()))
            c.commit()
        except Exception as e:
            log("migration", mid, repr(e))


# ── утилиты ───────────────────────────────────────────────────
def now():
    # utcnow() объявлен устаревшим в свежих Python — берём время с явной зоной.
    utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    return (utc + datetime.timedelta(hours=TIMEZONE)).isoformat(" ", "seconds")

def today():
    return now()[:10]

def money(n):
    return f"{int(n):,}".replace(",", " ") + " ₽"

def pts(n):
    return f"{int(n):,}".replace(",", " ")

def level_of(spent):
    lv = LOYALTY["levels"][0]
    for x in LOYALTY["levels"]:
        if spent >= x["from"]:
            lv = x
    return lv

def next_level(spent):
    for x in LOYALTY["levels"]:
        if spent < x["from"]:
            return x
    return None

def level_index(spent):
    """Порядковый номер уровня, начиная с нуля — для звёздочек на карте."""
    idx = 0
    for i, x in enumerate(LOYALTY["levels"]):
        if spent >= x["from"]:
            idx = i
    return idx

# ── гости ─────────────────────────────────────────────────────
def _next_card():
    """Номер карты: шесть цифр, непохожие друг на друга.

    Подряд идущие 1001, 1002, 1003 выглядели дёшево и подсказывали
    гостю, что он сорок второй клиент за всё время. Плюс по чужому
    номеру легко угадать соседний и назвать его официанту.

    Берём случайные шесть цифр, проверяя, что такой ещё не занят.
    Первая цифра не ноль — иначе номер теряется при копировании
    в таблицы, которые считают его числом.
    """
    c = conn()
    for _ in range(200):
        card = str(random.randint(100000, 999999))
        # Совсем некрасивые номера пропускаем: все цифры одинаковые
        # либо идут подряд — такие выглядят как ошибка.
        if len(set(card)) == 1:
            continue
        if not c.execute("SELECT 1 FROM guests WHERE card=?", (card,)).fetchone():
            return card
    # Свободных номеров почти не осталось — берём следующий по порядку.
    row = c.execute("SELECT MAX(CAST(card AS INTEGER)) m FROM guests").fetchone()
    return str((row["m"] or 100000) + 1)

def add_guest(tg_id, name="", username="", phone=""):
    with _lock:
        ex = get_by_tg(tg_id)
        if ex:
            return ex, False
        card = _next_card()
        w = LOYALTY["welcome"]
        cur = conn().execute(
            "INSERT INTO guests(tg_id,card,name,username,phone,bonus,created) VALUES(?,?,?,?,?,?,?)",
            (tg_id, card, name[:64], username[:64], phone, w, now()))
        gid = cur.lastrowid
        conn().execute(
            "INSERT INTO visits(guest_id,type,earned,at,by_user) VALUES(?,?,?,?,?)",
            (gid, "signup", w, now(), "система"))
        conn().commit()
        g = get(gid)
        queue_sheet("guest", g)
        return g, True

def get(gid):
    r = conn().execute("SELECT * FROM guests WHERE id=?", (gid,)).fetchone()
    return dict(r) if r else None

def get_by_tg(tg_id):
    r = conn().execute("SELECT * FROM guests WHERE tg_id=?", (tg_id,)).fetchone()
    return dict(r) if r else None

def get_by_card(card):
    """Гость по номеру карты. Пробелы и дефисы не мешают:
    гость называет «482 951», официант может так и записать."""
    digits = "".join(ch for ch in str(card) if ch.isdigit())
    if not digits:
        return None
    r = conn().execute("SELECT * FROM guests WHERE card=?", (digits,)).fetchone()
    return dict(r) if r else None

def find(q, limit=20):
    q = (q or "").strip()
    if not q:
        rows = conn().execute(
            "SELECT * FROM guests ORDER BY COALESCE(last_visit,created) DESC LIMIT ?", (limit,)).fetchall()
    else:
        digits = "".join(ch for ch in q if ch.isdigit())
        like = f"%{q.lower()}%"
        sql = ("SELECT * FROM guests WHERE lower(name) LIKE ? OR card LIKE ? "
               "OR lower(username) LIKE ?")
        args = [like, f"%{q}%", like]
        if len(digits) >= 3:
            sql += " OR replace(replace(replace(phone,' ',''),'-',''),'+','') LIKE ?"
            args.append(f"%{digits}%")
        sql += " ORDER BY COALESCE(last_visit,created) DESC LIMIT ?"
        args.append(limit)
        rows = conn().execute(sql, args).fetchall()
    return [dict(r) for r in rows]

def find_tg_id(username):
    """Найти Telegram ID человека по логину среди тех, кто писал боту.

    В Telegram нет способа спросить «какой ID у @vasya» — API такого
    метода не даёт. Зато у бота есть своя память: все, кто хоть раз
    ему написал, лежат в guests вместе с логинами. Оттуда и берём.

    Возвращает ID или 0, если человек боту ещё не писал.
    """
    u = norm_username(username)
    if not u:
        return 0
    r = conn().execute(
        "SELECT tg_id FROM guests WHERE lower(username)=? AND tg_id<>0 "
        "ORDER BY COALESCE(last_visit, created) DESC LIMIT 1", (u,)).fetchone()
    if r:
        return r["tg_id"]
    r = conn().execute(
        "SELECT tg_id FROM roles WHERE username=? AND tg_id<>0 LIMIT 1", (u,)).fetchone()
    return r["tg_id"] if r else 0


def remember_username(tg_id, username):
    """Держать логин гостя в актуальном виде.

    Человек может сменить ник в Telegram. Если не обновлять, поиск по
    логину начнёт находить не того. Обновляем при каждом обращении.
    """
    u = (username or "").strip().lstrip("@")
    if not tg_id or not u:
        return
    with _lock:
        c = conn()
        r = c.execute("SELECT id, username FROM guests WHERE tg_id=?", (tg_id,)).fetchone()
        if r and (r["username"] or "").lower() != u.lower():
            c.execute("UPDATE guests SET username=? WHERE id=?", (u[:64], r["id"]))
            c.commit()


def link_pending_roles():
    """Связать роли, выданные по логину, с реальными ID.

    Человека можно назначить директором до того, как он открыл бота.
    Когда он появится в базе гостей, ID подставится автоматически.
    Возвращает список записей, у которых ID только что нашёлся.
    """
    linked = []
    with _lock:
        c = conn()
        rows = c.execute("SELECT * FROM roles WHERE tg_id=0 AND username<>''").fetchall()
        for r in rows:
            found = find_tg_id(r["username"])
            if found:
                c.execute("UPDATE roles SET tg_id=? WHERE id=?", (found, r["id"]))
                linked.append({**dict(r), "tg_id": found})
        if linked:
            c.commit()
    return linked


def update(gid, **kw):
    allowed = {"name","phone","bday","note","blocked","muted","username"}
    sets, args = [], []
    for k, v in kw.items():
        if k in allowed:
            sets.append(f"{k}=?"); args.append(v)
    if not sets:
        return get(gid)
    args.append(gid)
    with _lock:
        conn().execute(f"UPDATE guests SET {','.join(sets)} WHERE id=?", args)
        conn().commit()
    g = get(gid)
    queue_sheet("guest", g)
    return g

def all_guests():
    return [dict(r) for r in conn().execute(
        "SELECT * FROM guests ORDER BY COALESCE(last_visit,created) DESC").fetchall()]

def count_guests():
    return conn().execute("SELECT COUNT(*) c FROM guests").fetchone()["c"]

# ── расчёт чека ───────────────────────────────────────────────
def preview(gid, total, use_pts=0):
    g = get(gid)
    if not g:
        return {"error": "Гость не найден"}
    if total <= 0:
        return {"error": "Сумма чека должна быть больше нуля"}
    if g["blocked"]:
        return {"error": "Карта заблокирована"}
    lv = level_of(g["spent"])
    max_pay = min(total * LOYALTY["max_pay_percent"] // 100, g["bonus"])
    pay = max(0, min(int(use_pts or 0), max_pay))
    to_pay = total - pay
    earned = to_pay * lv["cashback"] // 100
    return {"ok": True, "level": lv, "max_pay": max_pay, "pay": pay,
            "to_pay": to_pay, "earned": earned,
            "balance_after": g["bonus"] - pay + earned}

def _canonical_checkout_hash(gid, total, use_pts, items, by, hookah=False, redeem_hookah=False):
    """Stable SHA-256 of checkout body (sorted keys, coerced types)."""
    import hashlib
    body = {
        "by": str(by or ""),
        "gid": int(gid),
        "hookah": bool(hookah),
        "items": str(items or ""),
        "redeem_hookah": bool(redeem_hookah),
        "total": int(total),
        "use_pts": int(use_pts or 0),
    }
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def checkout(gid, total, use_pts=0, items="", by="", idempotency_key=None,
             hookah=False, redeem_hookah=False):
    """Conduct visit. Optional Idempotency-Key → single-commit with key row.

    On replay (same key + same body): returns stored result with replay=True.
    On same key + different body: {"error": "...", "code": "idempotency_mismatch"}.
    notify/sheets only when replay is False (caller should check).
    """
    total = int(total)
    use_pts = int(use_pts or 0)
    req_hash = _canonical_checkout_hash(
        gid, total, use_pts, items, by, hookah, redeem_hookah)

    with _lock:
        if idempotency_key:
            prev = conn().execute(
                "SELECT request_hash, response_json FROM idempotency_keys WHERE key=?",
                (idempotency_key,)).fetchone()
            if prev:
                if prev["request_hash"] != req_hash:
                    return {"error": "Повтор с другими данными",
                            "code": "idempotency_mismatch"}
                try:
                    cached = json.loads(prev["response_json"])
                except Exception:
                    cached = {"error": "Битый idempotency cache"}
                cached["replay"] = True
                return cached

        g = get(gid)
        if not g:
            return {"error": "Гость не найден"}
        if g["blocked"]:
            return {"error": "Карта заблокирована"}
        if total < 0:
            return {"error": "Сумма чека некорректна"}
        if total == 0 and not redeem_hookah:
            return {"error": "Сумма чека должна быть больше нуля"}

        lv = level_of(g["spent"])
        max_pay = min(total * LOYALTY["max_pay_percent"] // 100, g["bonus"]) if total else 0
        pay = max(0, min(int(use_pts or 0), max_pay))
        to_pay = total - pay
        earned = to_pay * lv["cashback"] // 100 if to_pay > 0 else 0

        extra, why = 0, []
        if not g["got_second"] and g["visits"] == 1 and total > 0:
            extra += LOYALTY["second_visit"]; why.append("второй визит")
        t = today()
        if g["bday"] and len(g["bday"]) >= 10 and g["bday"][5:10] == t[5:10] and g["got_bday"] != t[:4]:
            extra += LOYALTY["birthday"]; why.append("день рождения")

        stamp = int(g.get("stamp_count") or 0)
        free_pending = int(g.get("free_hookah_pending") or 0)
        if redeem_hookah and free_pending:
            free_pending = 0
            why.append("бесплатный кальян")
        if hookah and total > 0:
            stamp += 1
            if stamp >= 7:
                stamp = 0
                free_pending += 1
                why.append("штамп: free кальян")

        new_bonus = g["bonus"] - pay + earned + extra
        conn().execute("""UPDATE guests SET bonus=?, spent=?, visits=?, last_visit=?,
                          got_second=?, got_bday=?, stamp_count=?, free_hookah_pending=?
                          WHERE id=?""",
            (new_bonus, g["spent"] + to_pay, g["visits"] + (1 if total > 0 or redeem_hookah else 0),
             now(),
             1 if (g["got_second"] or "второй визит" in why) else 0,
             t[:4] if "день рождения" in why else g["got_bday"],
             stamp, free_pending, gid))
        conn().execute("""INSERT INTO visits(guest_id,type,total,paid_pts,paid_money,
                          earned,extra_why,items,at,by_user)
                          VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (gid, "visit", total, pay, to_pay, earned + extra,
             " + ".join(why), items, now(), by))

        g2 = get(gid)
        result = {"ok": True, "guest": g2, "earned": earned, "extra": extra,
                  "why": " + ".join(why), "paid": pay,
                  "level": level_of(g2["spent"]), "replay": False}

        if idempotency_key:
            # Store guest as dict-friendly JSON
            store = dict(result)
            store["guest"] = dict(g2) if g2 else None
            conn().execute(
                """INSERT INTO idempotency_keys(key, request_hash, response_json, created_at)
                   VALUES(?,?,?,?)""",
                (idempotency_key, req_hash,
                 json.dumps(store, ensure_ascii=False, default=str), now()))

        conn().commit()  # single commit: visit + guest + key

    g2 = result.get("guest") or get(gid)
    if not result.get("replay"):
        queue_sheet("guest", g2)
        queue_sheet("visit", {"card": g2["card"], "name": g2["name"], "type": "визит",
                              "total": total, "paid_pts": pay, "paid_money": to_pay,
                              "earned": earned + extra, "items": items,
                              "at": now(), "by": by, "why": " + ".join(why)})
    return result

def adjust(gid, delta, why="", by=""):
    with _lock:
        g = get(gid)
        if not g:
            return {"error": "Гость не найден"}
        if g["bonus"] + delta < 0:
            return {"error": "Баланс не может уйти в минус"}
        conn().execute("UPDATE guests SET bonus=? WHERE id=?", (g["bonus"] + delta, gid))
        conn().execute("""INSERT INTO visits(guest_id,type,earned,paid_pts,extra_why,at,by_user)
                          VALUES(?,?,?,?,?,?,?)""",
            (gid, "adjust", max(0, delta), max(0, -delta), why or "правка", now(), by))
        conn().commit()
    g2 = get(gid)
    queue_sheet("guest", g2)
    queue_sheet("visit", {"card": g2["card"], "name": g2["name"], "type": "правка",
                          "total": 0, "paid_pts": max(0, -delta), "paid_money": 0,
                          "earned": max(0, delta), "items": "", "at": now(),
                          "by": by, "why": why})
    return {"ok": True, "guest": g2}

def history(gid, limit=50):
    rows = conn().execute(
        "SELECT * FROM visits WHERE guest_id=? ORDER BY at DESC LIMIT ?", (gid, limit)).fetchall()
    return [dict(r) for r in rows]

def favourites(gid, top=5):
    cnt = {}
    for v in history(gid, 200):
        for part in (v["items"] or "").split(";"):
            part = part.strip()
            if not part:
                continue
            name, _, q = part.rpartition("×")
            name = (name or part).strip()
            try:
                q = int(q)
            except Exception:
                q = 1
            cnt[name] = cnt.get(name, 0) + q
    out = sorted(cnt.items(), key=lambda x: -x[1])
    return out[:top]

# ── купоны ────────────────────────────────────────────────────
def gen_code(n=6):
    al = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # без похожих символов
    while True:
        c = "".join(random.choice(al) for _ in range(n))
        if not conn().execute("SELECT 1 FROM coupons WHERE code=?", (c,)).fetchone():
            return c

def add_coupon(title, kind, value, min_check=0, uses=100, per_guest=1, until=""):
    code = gen_code()
    with _lock:
        conn().execute("""INSERT INTO coupons(code,title,kind,value,min_check,
                          uses_left,per_guest,until,created) VALUES(?,?,?,?,?,?,?,?,?)""",
            (code, title, kind, value, min_check, uses, per_guest, until, now()))
        conn().commit()
    return get_coupon(code)

def get_coupon(code):
    r = conn().execute("SELECT * FROM coupons WHERE code=?", (str(code).strip().upper(),)).fetchone()
    return dict(r) if r else None

def list_coupons(active_only=False):
    sql = "SELECT * FROM coupons"
    if active_only:
        sql += " WHERE active=1 AND uses_left>0"
    sql += " ORDER BY id DESC"
    return [dict(r) for r in conn().execute(sql).fetchall()]

def redeem_coupon(code, gid, by=""):
    with _lock:
        c = get_coupon(code)
        if not c:
            return {"error": "Купон не найден"}
        if not c["active"]:
            return {"error": "Купон отключён"}
        if c["uses_left"] <= 0:
            return {"error": "Купон закончился"}
        if c["until"] and today() > c["until"]:
            return {"error": f"Купон истёк {c['until']}"}
        used = conn().execute(
            "SELECT COUNT(*) n FROM coupon_uses WHERE coupon_id=? AND guest_id=?",
            (c["id"], gid)).fetchone()["n"]
        if used >= c["per_guest"]:
            return {"error": "Этот гость уже использовал купон"}
        g = get(gid)
        if not g:
            return {"error": "Гость не найден"}

        conn().execute("UPDATE coupons SET uses_left=uses_left-1 WHERE id=?", (c["id"],))
        conn().execute("INSERT INTO coupon_uses(coupon_id,guest_id,at) VALUES(?,?,?)",
                       (c["id"], gid, now()))
        conn().commit()

    if c["kind"] == "points":
        adjust(gid, c["value"], f"купон {c['code']} · {c['title']}", by)
    return {"ok": True, "coupon": c, "guest": get(gid)}

def toggle_coupon(code, active):
    with _lock:
        conn().execute("UPDATE coupons SET active=? WHERE code=?", (1 if active else 0, str(code).upper()))
        conn().commit()
    return get_coupon(code)

# ── сгорание бонусов ──────────────────────────────────────────
def burn_expired():
    days = LOYALTY.get("burn_days", 0)
    if not days:
        return []
    edge = (datetime.datetime.utcnow() + datetime.timedelta(hours=TIMEZONE)
            - datetime.timedelta(days=days)).isoformat(" ", "seconds")
    rows = conn().execute(
        """SELECT * FROM guests WHERE bonus>0 AND COALESCE(last_visit,created)<?""",
        (edge,)).fetchall()
    out = []
    for r in rows:
        g = dict(r)
        adjust(g["id"], -g["bonus"], f"сгорание через {days} дней без визитов", "система")
        out.append(g)
    return out

# ── роли ──────────────────────────────────────────────────────
# Роли живут в базе, а не в настройках хостинга: владелец раздаёт их
# кнопками в боте. Человека можно добавить по @username ещё до того,
# как он написал боту, — роль подхватится при первом обращении.
#
# owner — тот, кто поставил бота. Может всё, включая раздачу ролей.
# admin — директор заведения. Всё, кроме удаления владельца.
# staff — официант. Только приём чеков.

ROLE_NAMES = {"owner": "Владелец", "admin": "Директор", "staff": "Официант"}
ROLE_ORDER = {"owner": 0, "admin": 1, "staff": 2}


def norm_username(u):
    """@Vagdar1 → vagdar1. Пустая строка, если мусор."""
    u = (u or "").strip().lstrip("@").strip()
    if u.startswith("https://t.me/"):
        u = u[len("https://t.me/"):]
    elif u.startswith("t.me/"):
        u = u[len("t.me/"):]
    u = u.split("?")[0].split("/")[0]
    if not u or not all(ch.isalnum() or ch == "_" for ch in u):
        return ""
    return u.lower()


def grant(role, username="", tg_id=0, note="", by=""):
    """Выдать роль. По @username, по числовому ID или сразу по обоим.

    Если дали только логин — пробуем сразу найти ID среди тех, кто уже
    писал боту. Тогда человек получит уведомление о роли немедленно,
    а не при следующем входе.
    """
    username = norm_username(username)
    if not username and not tg_id:
        return None
    if username and not tg_id:
        tg_id = find_tg_id(username)
    with _lock:
        c = conn()
        row = None
        if tg_id:
            row = c.execute("SELECT * FROM roles WHERE tg_id=? AND tg_id<>0",
                            (tg_id,)).fetchone()
        if row is None and username:
            row = c.execute("SELECT * FROM roles WHERE username=?", (username,)).fetchone()
        if row:
            c.execute("UPDATE roles SET role=?, username=COALESCE(NULLIF(?,''),username), "
                      "tg_id=CASE WHEN ?<>0 THEN ? ELSE tg_id END, note=?, added_by=?, at=? "
                      "WHERE id=?",
                      (role, username, tg_id, tg_id, note or row["note"], by, now(), row["id"]))
        else:
            c.execute("INSERT INTO roles(tg_id, username, role, note, added_by, at) "
                      "VALUES(?,?,?,?,?,?)",
                      (tg_id, username, role, note, by, now()))
        c.commit()
        return get_role_row(username=username, tg_id=tg_id)


def get_role_row(username="", tg_id=0):
    c = conn()
    if tg_id:
        r = c.execute("SELECT * FROM roles WHERE tg_id=? AND tg_id<>0", (tg_id,)).fetchone()
        if r:
            return dict(r)
    username = norm_username(username)
    if username:
        r = c.execute("SELECT * FROM roles WHERE username=?", (username,)).fetchone()
        if r:
            return dict(r)
    return None


def role_of(tg_id, username=""):
    """Роль человека. Пусто — обычный гость.

    Если роль выдана по @username, а человек пишет впервые, его
    числовой ID запоминается — дальше смена ника ничего не сломает.
    """
    r = get_role_row(tg_id=tg_id)
    if r:
        return r["role"]
    uname = norm_username(username)
    if uname:
        r = get_role_row(username=uname)
        if r:
            if not r["tg_id"] and tg_id:
                with _lock:
                    c = conn()
                    c.execute("UPDATE roles SET tg_id=? WHERE id=?", (tg_id, r["id"]))
                    c.commit()
            return r["role"]
    return ""


def revoke(row_id, by=""):
    """Снять роль. Последнего владельца снять нельзя — иначе бот осиротеет."""
    with _lock:
        c = conn()
        r = c.execute("SELECT * FROM roles WHERE id=?", (row_id,)).fetchone()
        if not r:
            return False, "Запись не найдена"
        if r["role"] == "owner":
            n = c.execute("SELECT COUNT(*) n FROM roles WHERE role='owner'").fetchone()["n"]
            if n <= 1:
                return False, "Это единственный владелец — без него бота некому настраивать"
        c.execute("DELETE FROM roles WHERE id=?", (row_id,))
        c.commit()
        return True, ROLE_NAMES.get(r["role"], r["role"])


def list_roles(role=None):
    c = conn()
    if role:
        rows = c.execute("SELECT * FROM roles WHERE role=? ORDER BY at", (role,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM roles ORDER BY at").fetchall()
    out = [dict(r) for r in rows]
    out.sort(key=lambda r: (ROLE_ORDER.get(r["role"], 9), r["at"] or ""))
    return out


def count_owners():
    return conn().execute("SELECT COUNT(*) n FROM roles WHERE role='owner'").fetchone()["n"]


def seed_roles(owners=(), admins=(), staff=()):
    """Первичное наполнение из настроек — только если таблица пуста.

    Дальше роли живут в базе, и настройки хостинга их не перетирают:
    иначе снятая в боте роль возвращалась бы после перезапуска.
    """
    c = conn()
    if c.execute("SELECT COUNT(*) n FROM roles").fetchone()["n"]:
        return 0
    n = 0
    # Имя переменной не должно совпадать с функцией role():
    # после склейки модулей в один файл это перекрыло бы её.
    for group, kind in ((owners, "owner"), (admins, "admin"), (staff, "staff")):
        for item in group:
            item = str(item).strip()
            if not item:
                continue
            if item.lstrip("-").isdigit():
                grant(kind, tg_id=int(item), note="из настроек", by="система")
            else:
                grant(kind, username=item, note="из настроек", by="система")
            n += 1
    return n


# ── статистика ────────────────────────────────────────────────
def stats():
    c = conn()
    total = c.execute("SELECT COUNT(*) n FROM guests").fetchone()["n"]
    vis = c.execute("SELECT COUNT(*) n, COALESCE(SUM(paid_money),0) s, "
                    "COALESCE(SUM(total),0) t FROM visits WHERE type='visit'").fetchone()
    liab = c.execute("SELECT COALESCE(SUM(bonus),0) s FROM guests").fetchone()["s"]
    given = c.execute("SELECT COALESCE(SUM(earned),0) s FROM visits").fetchone()["s"]
    used = c.execute("SELECT COALESCE(SUM(paid_pts),0) s FROM visits").fetchone()["s"]
    edge30 = (datetime.datetime.utcnow() + datetime.timedelta(hours=TIMEZONE)
              - datetime.timedelta(days=30)).isoformat(" ", "seconds")
    act = c.execute("SELECT COUNT(*) n FROM guests WHERE last_visit>?", (edge30,)).fetchone()["n"]
    today_ = c.execute("SELECT COUNT(*) n, COALESCE(SUM(paid_money),0) s FROM visits "
                       "WHERE type='visit' AND at>=?", (today() + " 00:00:00",)).fetchone()

    items = {}
    for r in c.execute("SELECT items FROM visits WHERE items<>''").fetchall():
        for part in (r["items"] or "").split(";"):
            part = part.strip()
            if not part:
                continue
            name, _, q = part.rpartition("×")
            name = (name or part).strip()
            try:
                q = int(q)
            except Exception:
                q = 1
            items[name] = items.get(name, 0) + q
    top = sorted(items.items(), key=lambda x: -x[1])[:10]

    lv = []
    for l in LOYALTY["levels"]:
        n = c.execute("SELECT COUNT(*) n FROM guests WHERE spent>=?", (l["from"],)).fetchone()["n"]
        lv.append((l["name"], n))
    # превращаем «больше или равно» в «ровно этот уровень»
    lv2 = []
    for i, (name, n) in enumerate(lv):
        nxt = lv[i + 1][1] if i + 1 < len(lv) else 0
        lv2.append((name, n - nxt))

    return {"guests": total, "active30": act, "visits": vis["n"],
            "revenue": vis["s"], "turnover": vis["t"],
            "avg": (vis["s"] // vis["n"]) if vis["n"] else 0,
            "liability": liab, "given": given, "used": used,
            "today_visits": today_["n"], "today_revenue": today_["s"],
            "top": top, "levels": lv2}

# ── очередь выгрузки в Google Таблицу ─────────────────────────
def queue_sheet(kind, data):
    if not SHEETS_URL:
        return
    try:
        payload = json.dumps({"kind": kind, "data": data}, ensure_ascii=False, default=str)
        with _lock:
            conn().execute("INSERT INTO sheet_queue(payload,at) VALUES(?,?)", (payload, now()))
            conn().commit()
    except Exception:
        pass

def take_queue(limit=20):
    rows = conn().execute("SELECT * FROM sheet_queue ORDER BY id LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def drop_queue(ids):
    if not ids:
        return
    with _lock:
        conn().executemany("DELETE FROM sheet_queue WHERE id=?", [(i,) for i in ids])
        conn().commit()

def bump_queue(qid):
    with _lock:
        conn().execute("UPDATE sheet_queue SET tries=tries+1 WHERE id=?", (qid,))
        conn().execute("DELETE FROM sheet_queue WHERE id=? AND tries>8", (qid,))
        conn().commit()

# ── CSV ───────────────────────────────────────────────────────
def csv_guests():
    rows = [["Карта","Имя","Username","Телефон","День рождения","Уровень",
             "Бонусов","Визитов","Сумма чеков","Последний визит","Что обычно берёт"]]
    for g in all_guests():
        fav = "; ".join(f"{t} ×{n}" for t, n in favourites(g["id"], 3))
        rows.append([g["card"], g["name"], g["username"], g["phone"], g["bday"],
                     level_of(g["spent"])["name"], g["bonus"], g["visits"],
                     g["spent"], (g["last_visit"] or "")[:16], fav])
    return _csv(rows)

def csv_visits():
    rows = [["Дата","Карта","Гость","Тип","Сумма чека","Бонусами",
             "Деньгами","Начислено","Причина","Позиции","Провёл"]]
    q = """SELECT v.*, g.card, g.name FROM visits v
           LEFT JOIN guests g ON g.id=v.guest_id ORDER BY v.at DESC"""
    names = {"visit": "визит", "signup": "регистрация", "adjust": "правка"}
    for r in conn().execute(q).fetchall():
        rows.append([r["at"], r["card"] or "—", r["name"] or "удалён",
                     names.get(r["type"], r["type"]), r["total"], r["paid_pts"],
                     r["paid_money"], r["earned"], r["extra_why"] or "",
                     r["items"] or "", r["by_user"] or ""])
    return _csv(rows)

def _csv(rows):
    out = []
    for r in rows:
        out.append(";".join('"' + str(c if c is not None else "").replace('"', '""') + '"' for c in r))
    return "\ufeff" + "\r\n".join(out)


# ══════════════════════════════════════════════════════════════
#  СВЯЗЬ С TELEGRAM
# ══════════════════════════════════════════════════════════════
"""Тонкая обёртка над Telegram Bot API. Только стандартная библиотека."""
import json, urllib.request, urllib.parse, urllib.error, time, threading

API = "https://api.telegram.org/bot{}/{}"
_log_lock = threading.Lock()

def log(*a):
    line = " ".join(str(x) for x in a)
    stamp = time.strftime("%H:%M:%S")
    with _log_lock:
        print(f"[{stamp}] {line}", flush=True)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
        except Exception:
            pass

def call(method, **params):
    """Вызов метода API. Возвращает result или None."""
    url = API.format(TOKEN, method)
    data = {}
    for k, v in params.items():
        if v is None:
            continue
        data[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
    body = urllib.parse.urlencode(data).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=65) as r:
                res = json.loads(r.read().decode())
                if res.get("ok"):
                    return res.get("result")
                desc = res.get("description", "")
                if "retry after" in desc.lower():
                    wait = int(res.get("parameters", {}).get("retry_after", 3))
                    time.sleep(wait + 1); continue
                log("API ошибка:", method, desc)
                return None
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode())
                desc = err.get("description", str(e))
            except Exception:
                desc = str(e)
            if e.code == 429:
                time.sleep(3); continue
            if e.code in (400, 403):
                log("API", e.code, method, desc)
                return None
            log("HTTP", e.code, method, desc)
        except Exception as e:
            if attempt == 2:
                log("Сеть:", method, repr(e))
            time.sleep(1.5)
    return None

def send(chat_id, text, kb=None, preview=False, parse="HTML"):
    return call("sendMessage", chat_id=chat_id, text=text[:4096],
                reply_markup=kb, parse_mode=parse,
                link_preview_options={"is_disabled": not preview})

def edit(chat_id, mid, text, kb=None, parse="HTML"):
    return call("editMessageText", chat_id=chat_id, message_id=mid,
                text=text[:4096], reply_markup=kb, parse_mode=parse,
                link_preview_options={"is_disabled": True})

def answer(cb_id, text=None, alert=False):
    return call("answerCallbackQuery", callback_query_id=cb_id, text=text, show_alert=alert)

def delete(chat_id, mid):
    return call("deleteMessage", chat_id=chat_id, message_id=mid)

def _mime_of(filename):
    """Тип содержимого по расширению файла."""
    low = filename.lower()
    if low.endswith(".csv"):
        return "text/csv; charset=utf-8"
    if low.endswith(".txt") or low.endswith(".log") or low.endswith(".md"):
        return "text/plain; charset=utf-8"
    if low.endswith(".json"):
        return "application/json; charset=utf-8"
    return "application/octet-stream"

def send_doc(chat_id, filename, content, caption=""):
    """Отправка файла без сторонних библиотек — multipart собираем руками.

    content: строка (будет закодирована в UTF-8) или bytes.
    Тип содержимого выбирается по расширению — бинарные файлы (.db)
    уходят как application/octet-stream и не портятся.
    """
    url = API.format(TOKEN, "sendDocument")
    boundary = "----ispoved" + str(int(time.time() * 1000))
    if isinstance(content, str):
        content = content.encode("utf-8")
    parts = []
    def field(name, value):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    field("chat_id", str(chat_id))
    if caption:
        field("caption", caption[:1000])
        field("parse_mode", "HTML")
    parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; "
                  f"filename=\"{filename}\"\r\nContent-Type: {_mime_of(filename)}\r\n\r\n").encode())
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    try:
        req = urllib.request.Request(url, data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode()).get("ok")
    except Exception as e:
        log("Файл не отправлен:", repr(e))
        return False

def send_photo(chat_id, filename, content, caption="", kb=None):
    """Отправка картинки. Multipart собираем вручную, без библиотек."""
    url = API.format(TOKEN, "sendPhoto")
    boundary = "----ispovedimg" + str(int(time.time() * 1000))
    parts = []
    def field(name, value):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; "
                     f"name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    field("chat_id", str(chat_id))
    if caption:
        field("caption", caption[:1024])
        field("parse_mode", "HTML")
    if kb:
        field("reply_markup", json.dumps(kb, ensure_ascii=False))
    parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; "
                  f"filename=\"{filename}\"\r\nContent-Type: image/png\r\n\r\n").encode())
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    try:
        req = urllib.request.Request(url, data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=90) as r:
            res = json.loads(r.read().decode())
            return res.get("result") if res.get("ok") else None
    except Exception as e:
        log("Картинка не отправлена:", repr(e))
        return None


def download(file_id, max_bytes=40 * 1024 * 1024):
    """Скачивание файла, присланного в чат. Возвращает bytes или None."""
    info = call("getFile", file_id=file_id)
    if not info or not info.get("file_path"):
        return None
    size = info.get("file_size") or 0
    if size > max_bytes:
        log("Файл слишком большой:", size)
        return None
    url = "https://api.telegram.org/file/bot{}/{}".format(TOKEN, info["file_path"])
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read(max_bytes + 1)
        if len(data) > max_bytes:
            log("Файл превысил лимит при чтении")
            return None
        return data
    except Exception as e:
        log("Файл не скачан:", repr(e))
        return False if False else None

# ── клавиатуры ────────────────────────────────────────────────
def kb(rows):
    """rows = [[('текст','данные'), ...], ...]"""
    out = []
    for row in rows:
        r = []
        for item in row:
            if item is None:
                continue
            text, data = item[0], item[1]
            if isinstance(data, dict):
                r.append({"text": text, **data})
            elif str(data).startswith("http"):
                r.append({"text": text, "url": data})
            else:
                r.append({"text": text, "callback_data": str(data)})
        if r:
            out.append(r)
    return {"inline_keyboard": out}

def reply_kb(rows, once=False):
    return {"keyboard": [[{"text": t} for t in row] for row in rows],
            "resize_keyboard": True, "one_time_keyboard": once}

def remove_kb():
    return {"remove_keyboard": True}

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ══════════════════════════════════════════════════════════════
#  РЕЗЕРВНЫЕ КОПИИ
# ══════════════════════════════════════════════════════════════
"""
Резервные копии базы.

Зачем: на хостингах вроде Bothost файлы внутри контейнера пропадают
при каждой пересборке. Бот раз в сутки отправляет копию базы админам
в личку. Telegram хранит файлы бесплатно и долго.

Восстановление: админ пересылает боту файл .db — бот проверяет его
и заменяет текущую базу, сделав копию старой рядом.

Только стандартная библиотека.
"""

# Таблицы, которые обязаны быть в настоящей базе «Исповеди».
REQUIRED_TABLES = {"guests", "visits", "coupons"}

MAX_DB_BYTES = 40 * 1024 * 1024   # Telegram не примет документ крупнее ~50 МБ


def db_size():
    """Размер файла базы в байтах. 0 — если файла ещё нет."""
    try:
        return os.path.getsize(DB_PATH)
    except OSError:
        return 0


def human_size(n):
    """Размер по-человечески: 812 Б, 41.2 КБ, 3.1 МБ."""
    n = float(n)
    if n < 1024:
        return f"{int(n)} Б"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} КБ"
    return f"{n / (1024 * 1024):.1f} МБ"


def make_copy(dest=None):
    """Согласованная копия базы.

    Обычный shutil.copy опасен: в режиме WAL часть свежих данных лежит
    в отдельном файле -wal, и копия может оказаться битой. Поэтому
    используем родной механизм SQLite backup — он даёт целостный снимок
    даже во время записи.

    Возвращает путь к копии.
    """
    if dest is None:
        dest = DB_PATH + ".tmp"
    if os.path.exists(dest):
        try:
            os.remove(dest)
        except OSError:
            pass
    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return dest


def backup_bytes():
    """Содержимое согласованной копии базы как bytes. None — если не вышло."""
    tmp = None
    try:
        tmp = make_copy()
        size = os.path.getsize(tmp)
        if size > MAX_DB_BYTES:
            return None
        with open(tmp, "rb") as f:
            return f.read()
    except Exception:
        return None
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def backup_name(stamp=None):
    """Имя файла копии с датой: ispoved-2026-08-05.db"""
    stamp = stamp or time.strftime("%Y-%m-%d")
    return f"ispoved-{stamp}.db"


def check_db_file(path):
    """Проверка присланного файла.

    Возвращает (ok, сообщение, сводка). Сводка — словарь с числом
    гостей и визитов, если файл годный.
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return False, "Файл не найден", {}
    if size < 100:
        return False, "Файл пустой или обрезан", {}

    # Настоящая база SQLite всегда начинается с этой подписи.
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError:
        return False, "Файл не читается", {}
    if head != b"SQLite format 3\x00":
        return False, "Это не файл базы SQLite", {}

    try:
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
    except Exception:
        return False, "База не открывается", {}
    try:
        integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            return False, "База повреждена", {}
        names = {r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        missing = REQUIRED_TABLES - names
        if missing:
            return False, "Это база от другого бота: нет таблиц " + ", ".join(sorted(missing)), {}
        # В таблице visits лежат и визиты, и правки бонусов. Считаем только
        # визиты — чтобы число совпадало с тем, что админ видит в статистике.
        try:
            visits = c.execute(
                "SELECT COUNT(*) FROM visits WHERE type='visit'").fetchone()[0]
        except Exception:
            visits = c.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
        summary = {
            "guests": c.execute("SELECT COUNT(*) FROM guests").fetchone()[0],
            "visits": visits,
            "size":   size,
        }
        return True, "ok", summary
    except Exception as e:
        return False, f"Ошибка чтения базы: {e}", {}
    finally:
        c.close()


def restore(path):
    """Замена текущей базы присланным файлом.

    Старая база не удаляется — переименовывается с меткой времени,
    чтобы можно было откатиться, если восстановили не то.
    Возвращает (ok, сообщение).
    """
    ok, why, _ = check_db_file(path)
    if not ok:
        return False, why

    with _lock:
        close()
        stamp = time.strftime("%Y%m%d-%H%M%S")
        if os.path.exists(DB_PATH):
            try:
                shutil.move(DB_PATH, f"{DB_PATH}.before-{stamp}")
            except OSError:
                pass
        # Хвосты WAL от прежней базы обязаны уйти, иначе смешаются с новой.
        for suffix in ("-wal", "-shm"):
            leftover = DB_PATH + suffix
            if os.path.exists(leftover):
                try:
                    os.remove(leftover)
                except OSError:
                    pass
        shutil.copyfile(path, DB_PATH)
        conn()
    return True, "Восстановлено"


def send_to_admins(tg, admins, reason="ежедневная копия"):
    """Отправка копии базы всем админам. Возвращает число доставленных."""
    data = backup_bytes()
    if data is None:
        return 0
    try:
        s = stats()
        line = f"👥 {s['guests']} гостей · 🧾 {s['visits']} визитов"
    except Exception:
        line = ""
    caption = (f"💾 <b>Копия базы</b> · {reason}\n"
               f"{line}\n"
               f"Размер: {human_size(len(data))}\n\n"
               f"Храните это сообщение. Чтобы восстановить — "
               f"перешлите файл боту.")
    sent = 0
    for a in admins:
        try:
            if send_doc(a, backup_name(), data, caption):
                sent += 1
        except Exception:
            pass
    return sent


def worker(tg, hour=5, who=None):
    """Фоновая задача: раз в сутки в указанный час шлёт копию админам.

    who — функция, возвращающая список получателей. Роли живут в базе
    и меняются на ходу, поэтому список берём каждый раз заново.
    """
    last = ""
    while True:
        try:
            # Имя переменной не должно совпадать с функцией now():
            # после склейки всех модулей в один файл это перекрывает её.
            stamp = now()        # уже в часовом поясе заведения
            day, clock = stamp[:10], stamp[11:13]
            if day != last and clock >= f"{hour:02d}":
                if count_guests() > 0:
                    send_to_admins(tg, who() if who else [])
                last = day
        except Exception as e:
            try:
                log("Резервная копия:", repr(e))
            except Exception:
                pass
        time.sleep(600)


# ══════════════════════════════════════════════════════════════
#  ЛОГИКА БОТА
# ══════════════════════════════════════════════════════════════
"""
Бот «Исповедь» — карта лояльности.
Три роли, полностью изолированные: гость / официант / администратор.
Запуск: python3 bot.py
"""

BOT_NAME = ""
LAST_SEEN = {}
# dialog state lives in SQLite (dialog_state) — survives restarts
MAINTENANCE = False  # set True during DB restore

# ══════════════════════════════════════════════════════════════
#  РОЛИ
# ══════════════════════════════════════════════════════════════
USERNAMES = {}      # tg_id -> @username, запоминаем при каждом сообщении

def role(uid, username=""):
    """Роль по базе. Владелец и директор одинаково видят админку."""
    r = role_of(uid, username or USERNAMES.get(uid, ""))
    if r in ("owner", "admin"):
        return "admin"
    if r == "staff":
        return "staff"
    return "guest"

def raw_role(uid, username=""):
    """Точная роль: owner / admin / staff / '' — для прав на раздачу ролей."""
    return role_of(uid, username or USERNAMES.get(uid, ""))

def is_owner(uid): return raw_role(uid) == "owner"
def is_admin(uid): return role(uid) == "admin"
def is_staff(uid): return role(uid) in ("admin", "staff")

def admin_ids():
    """Кому слать служебные уведомления: владельцы и директора.

    Берём из базы, а не из настроек хостинга: роли раздаются в боте.
    Те, кто добавлен по @username и ещё ни разу не писал, пропускаются —
    им просто некуда отправить.
    """
    out = []
    for r in list_roles():
        if r["role"] in ("owner", "admin") and r["tg_id"]:
            out.append(r["tg_id"])
    return out

# ══════════════════════════════════════════════════════════════
#  СОСТОЯНИЕ ДИАЛОГА (SQLite — переживает рестарт)
# ══════════════════════════════════════════════════════════════
def set_state(uid, mode, **data):
    with _lock:
        conn().execute(
            """INSERT INTO dialog_state(tg_id, mode, data_json, updated_at)
               VALUES(?,?,?,?)
               ON CONFLICT(tg_id) DO UPDATE SET
                 mode=excluded.mode,
                 data_json=excluded.data_json,
                 updated_at=excluded.updated_at""",
            (int(uid), mode or "", json.dumps(data, ensure_ascii=False), now()))
        conn().commit()

def get_state(uid):
    r = conn().execute(
        "SELECT mode, data_json FROM dialog_state WHERE tg_id=?",
        (int(uid),)).fetchone()
    if not r:
        return None
    try:
        data = json.loads(r["data_json"] or "{}")
    except Exception:
        data = {}
    return {"mode": r["mode"], "data": data}

def clear_state(uid):
    with _lock:
        conn().execute("DELETE FROM dialog_state WHERE tg_id=?", (int(uid),))
        conn().commit()

# ══════════════════════════════════════════════════════════════
#  ГОСТЬ
# ══════════════════════════════════════════════════════════════
def send_card_qr(uid, g):
    """Карта гостя картинкой с QR-кодом.

    В коде — только номер карты. Официант сканирует и сразу видит гостя,
    ничего не переспрашивая. Никаких персональных данных внутрь не кладём:
    код виден любому, кто окажется рядом с экраном.
    """
    try:
        img = png(str(g["card"]), scale=8, quiet=4)
    except Exception as e:
        log("QR не построился:", repr(e))
        send(uid, guest_card_text(g), guest_menu(g))
        return
    lv = level_of(g["spent"])
    cap = (f"◆ <b>{esc(BRAND['name'])}</b> · карта лояльности\n\n"
           f"<b>{esc(g['name'] or 'Гость')}</b> · {esc(lv['name'])}\n"
           f"№ <code>{pretty_card(g['card'])}</code>\n"
           f"Баланс: <b>{pts(g['bonus'])}</b> бонусов\n\n"
           f"<i>Покажите QR официанту при оплате</i>")
    ok = send_photo(uid, f"card-{g['card']}.png", img, cap,
                       kb([[("← В меню", "g:card")]]))
    if not ok:
        send(uid, guest_card_text(g), guest_menu(g))


def guest_menu(g):
    rows = [
        [("QR-код для зала", "g:qr")],
        [("Моя карта", "g:card"), ("Бонусы и уровни", "g:bonus")],
        [("Меню заведения", "g:menu"), ("История", "g:hist")],
        [("Ввести купон", "g:coupon")],
        [("Забронировать стол", "g:book")],
        [("Написать директору", "g:dm")],
        [("Профиль", "g:prof")],
    ]
    if WEBAPP_URL:
        rows.insert(0, [("Открыть приложение", {"web_app": {"url": WEBAPP_URL}})])
    return kb(rows)

def progress_bar(done, total, width=10):
    """Полоса прогресса символами: ▰▰▰▱▱▱▱▱▱▱"""
    if total <= 0:
        return "▰" * width
    filled = max(0, min(width, round(done * width / total)))
    return "▰" * filled + "▱" * (width - filled)


def pretty_card(card):
    """Номер карты группами по три: 482 951 — так его легче назвать вслух."""
    s = str(card)
    if len(s) == 6:
        return f"{s[:3]} {s[3:]}"
    return s


def guest_card_text(g):
    lv = level_of(g["spent"])
    nx = next_level(g["spent"])
    stars = "★" * (level_index(g["spent"]) + 1) + \
            "☆" * (len(LOYALTY["levels"]) - level_index(g["spent"]) - 1)
    first = (g.get("name") or "Гость").split()[0]

    t = (f"<b>{esc(BRAND['name'])}</b> · {esc(BRAND['kind'])}\n"
         f"{esc(BRAND['city'])}, {esc(BRAND['addr'])}\n"
         f"────────────────────\n\n"
         f"Здравствуйте, <b>{esc(first)}</b>\n"
         f"Карта <code>{pretty_card(g['card'])}</code>\n\n"
         f"<b>{pts(g['bonus'])}</b> бонусов на счёте\n"
         f"{stars}  <b>{esc(lv['name'])}</b> · кэшбэк <b>{lv['cashback']}%</b>\n\n")

    if nx:
        prev = lv["from"]
        need = nx["from"] - g["spent"]
        bar = progress_bar(g["spent"] - prev, nx["from"] - prev)
        t += (f"{bar}\n"
              f"До уровня «{esc(nx['name'])}» — {money(need)}\n"
              f"<i>кэшбэк станет {nx['cashback']}%</i>\n\n")
    else:
        t += "<b>Максимальный уровень</b> — спасибо, что вы с нами\n\n"

    stamp = int(g.get("stamp_count") or 0)
    free_h = int(g.get("free_hookah_pending") or 0)
    t += (f"Отметки кальяна: <b>{stamp}/7</b>"
          + (f" · free: <b>{free_h}</b>" if free_h else "")
          + "\n"
          f"Визитов: {g['visits']} · всего {money(g['spent'])}\n\n")

    if WEBAPP_URL:
        t += "<i>Удобнее в приложении — кнопка «Открыть приложение» ниже.\n"
        t += "В зале покажите QR или назовите номер карты.</i>"
    else:
        t += "<i>В зале покажите QR или назовите номер карты официанту.</i>"
    return t

def guest_start(uid, msg):
    u = msg.get("from", {})
    name = " ".join(x for x in [u.get("first_name"), u.get("last_name")] if x)
    g, new = add_guest(uid, name, u.get("username", ""))
    if new:
        first = (name or "друг").split()[0]
        welcome = (
            f"<b>Добро пожаловать в «{esc(BRAND['name'])}»</b>\n\n"
            f"{esc(first)}, ваша карта лояльности готова.\n\n"
            f"Номер: <code>{pretty_card(g['card'])}</code>\n"
            f"Начислено: <b>+{pts(LOYALTY['welcome'])}</b> бонусов в подарок\n\n"
            f"· кэшбэк <b>{LOYALTY['cashback']}%</b> с каждого чека\n"
            f"· бонусами можно оплатить до <b>{LOYALTY['max_pay_percent']}%</b> счёта\n"
            f"· каждый 8-й кальян — бесплатно (по отметкам)\n\n"
        )
        if WEBAPP_URL:
            welcome += "Откройте <b>приложение</b> — там карта, QR и прогресс.\n"
            welcome += "Или пользуйтесь кнопками меню ниже."
        else:
            welcome += "Ниже — ваша карта и меню."
        send(uid, welcome)
        send_card_qr(uid, g)
        send(uid, guest_card_text(g), guest_menu(g))
        for a in admin_ids():
            send(a, f"Новый гость: <b>{esc(name or '—')}</b>\n"
                       f"Карта <code>{pretty_card(g['card'])}</code>")
    else:
        first = (g.get("name") or name or "друг").split()[0]
        send(uid,
             f"С возвращением, <b>{esc(first)}</b>\n\n" + guest_card_text(g),
             guest_menu(g))

def guest_cb(uid, data, cb, g):
    mid = cb["message"]["message_id"]
    act = data[2:]

    if act == "card":
        edit(uid, mid, guest_card_text(g), guest_menu(g))

    elif act == "qr":
        send_card_qr(uid, g)

    elif act == "bonus":
        lv = level_of(g["spent"])
        t = (f"<b>Программа лояльности</b>\n\n"
             f"Сейчас у вас: <b>{pts(g['bonus'])}</b> бонусов\n"
             f"Ваш уровень: <b>{esc(lv['name'])}</b> · кэшбэк <b>{lv['cashback']}%</b>\n\n"
             f"<b>Правила</b>\n"
             f"· кэшбэк с оплаченной части чека\n"
             f"· бонусами — до <b>{LOYALTY['max_pay_percent']}%</b> счёта\n"
             f"· в день рождения: <b>+{pts(LOYALTY['birthday'])}</b> (при визите)\n"
             f"· 7 отметок за кальян → 8-й в подарок\n")
        if LOYALTY.get("burn_days"):
            t += f"· без визитов {LOYALTY['burn_days']} дней бонусы сгорают\n"
        t += "\n<b>Уровни</b>\n"
        for l in LOYALTY["levels"]:
            mark = "→ " if l["name"] == lv["name"] else "   "
            t += f"{mark}<b>{esc(l['name'])}</b> — от {money(l['from'])}, кэшбэк {l['cashback']}%\n"
        t += "\n<i>1 бонус = 1 ₽ при оплате в заведении</i>"
        edit(uid, mid, t, kb([[("← К карте", "g:card")]]))

    elif act == "menu":
        try:
            cats = MENU
        except Exception:
            cats = []
        if not cats:
            answer(cb["id"], "Меню пока не заполнено", True); return
        rows = [[(c["t"] + (" · 18+" if c.get("alco") else ""), f"g:mc:{c['id']}")]
                for c in cats]
        rows.append([("← К карте", "g:card")])
        edit(uid, mid,
             f"<b>Меню «{esc(BRAND['name'])}»</b>\n\n"
             f"Выберите раздел. Цены — ориентир; актуальные уточняйте в зале.",
             kb(rows))

    elif act.startswith("mc:"):
        cid = act[3:]
        pass
        cat = next((c for c in MENU if c["id"] == cid), None)
        if not cat:
            answer(cb["id"], "Раздел не найден", True); return
        t = f"<b>{esc(cat['t'])}</b>\n\n"
        for it in cat["items"]:
            tag = f" · <i>{esc(it['tag'])}</i>" if it.get("tag") else ""
            t += f"<b>{esc(it['t'])}</b> — {money(it['p'])}{tag}\n"
            if it.get("d"):
                t += f"<i>{esc(it['d'])}</i>\n"
            t += "\n"
        if cat.get("alco"):
            t += ("<i>18+. Алкоголь продаётся лицам старше 18 лет. "
                  "Чрезмерное употребление вредит вашему здоровью.</i>\n")
        # Длинные разделы не влезают в одно сообщение Telegram.
        if len(t) > 4000:
            t = t[:3900].rsplit("\n\n", 1)[0] + \
                "\n\n<i>Полный список — в зале или у официанта.</i>"
        edit(uid, mid, t, kb([[("← К разделам", "g:menu")], [("🏠 Карта", "g:card")]]))

    elif act == "hist":
        h = history(g["id"], 10)
        if not h:
            edit(uid, mid, "Пока пусто. Здесь появятся визиты и начисления.",
                    kb([[("← Назад", "g:card")]])); return
        t = "<b>Последние операции</b>\n\n"
        for v in h:
            when = (v["at"] or "")[:16]
            if v["type"] == "signup":
                t += f"🎁 {when}\nКарта выпущена · +{pts(v['earned'])}\n\n"
            elif v["type"] == "adjust":
                sign = f"+{pts(v['earned'])}" if v["earned"] else f"−{pts(v['paid_pts'])}"
                t += f"✏️ {when}\n{esc(v['extra_why'] or 'правка')} · {sign}\n\n"
            else:
                line = f"🧾 {when}\nЧек {money(v['total'])}"
                if v["paid_pts"]:
                    line += f" · списано {pts(v['paid_pts'])}"
                if v["earned"]:
                    line += f" · +{pts(v['earned'])}"
                if v["extra_why"]:
                    line += f"\n🎉 {esc(v['extra_why'])}"
                if v["items"]:
                    line += f"\n<i>{esc(v['items'][:90])}</i>"
                t += line + "\n\n"
        fav = favourites(g["id"], 3)
        if fav:
            t += "<b>Вы обычно берёте:</b>\n" + "\n".join(f"• {esc(n)} ×{q}" for n, q in fav)
        edit(uid, mid, t, kb([[("← Назад", "g:card")]]))

    elif act == "coupon":
        set_state(uid, "coupon")
        edit(uid, mid, "🎟 <b>Введите код купона</b>\n\nОтправьте код сообщением.",
                kb([[("Отмена", "g:card")]]))

    elif act == "book":
        set_state(uid, "book")
        edit(uid, mid,
            "📅 <b>Бронь стола</b>\n\nНапишите одним сообщением: дату, время и число гостей.\n"
            "<i>Например: 12 августа, 20:00, 4 человека</i>",
            kb([[("Отмена", "g:card")]]))

    elif act == "dm":
        set_state(uid, "dm")
        edit(uid, mid,
            "✉️ <b>Сообщение директору</b>\n\nНапишите, что понравилось или что стоит исправить. "
            "Читает лично.",
            kb([[("Отмена", "g:card")]]))

    elif act == "prof":
        show_profile(uid, mid, g)

    elif act == "mute":
        g2 = update(g["id"], muted=0 if g.get("muted") else 1)
        answer(cb["id"],
                  "Уведомления выключены" if g2.get("muted") else "Уведомления включены",
                  True)
        show_profile(uid, mid, g2)

    elif act == "setbday":
        set_state(uid, "bday")
        edit(uid, mid,
            f"🎂 <b>Дата рождения</b>\n\n"
            f"Напишите её в виде <code>15.03.1998</code> или <code>15.03</code>.\n\n"
            f"В день рождения начислим <b>{pts(LOYALTY['birthday'])}</b> "
            f"бонусов — подарок от заведения.\n\n"
            f"<i>Дату можно указать один раз, потом менять только через "
            f"администратора — чтобы подарок не получали каждый месяц.</i>",
            kb([[("Отмена", "g:prof")]]))

    elif act == "setphone":
        set_state(uid, "phone")
        edit(uid, mid,
            "📞 <b>Телефон</b>\n\n"
            "Напишите номер, например <code>+7 912 345-67-89</code>.\n\n"
            "Нужен, чтобы подтвердить бронь стола и вернуть карту, "
            "если потеряете доступ к Telegram.",
            kb([[("Отмена", "g:prof")]]))

def show_profile(uid, mid, g):
    """Профиль гостя: что он может дозаполнить сам."""
    bday = g.get("bday") or ""
    phone = g.get("phone") or ""
    t = (f"⚙️ <b>Мой профиль</b>\n\n"
         f"👤 {esc(g['name'] or '—')}\n"
         f"🎫 Карта <code>{pretty_card(g['card'])}</code>\n"
         f"📞 {esc(phone) if phone else '<i>не указан</i>'}\n"
         f"🎂 {esc(pretty_bday(bday)) if bday else '<i>не указана</i>'}\n\n")
    if not bday:
        t += (f"<i>Укажите дату рождения — подарим "
              f"{pts(LOYALTY['birthday'])} бонусов в ваш день.</i>\n")
    rows = []
    if not bday:
        rows.append([("🎂 Указать день рождения", "g:setbday")])
    rows.append([("📞 Изменить телефон" if phone else "📞 Указать телефон",
                  "g:setphone")])
    rows.append([("🔕 Отключить уведомления" if not g.get("muted")
                  else "🔔 Включить уведомления", "g:mute")])
    rows.append([("← Назад", "g:card")])
    edit(uid, mid, t, kb(rows))


def parse_bday(text):
    """Разобрать дату рождения. Возвращает ГГГГ-ММ-ДД или пусто.

    Принимаем «15.03.1998», «15.03», «15/03/1998», «15 марта».
    Год необязателен: для подарка важны только день и месяц.
    """
    s = (text or "").strip().lower()
    MONTHS = {
        "янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "май": 5,
        "июн": 6, "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
    }
    day = month = year = 0

    m = re.match(r"^(\d{1,2})\s*[.\-/ ]\s*(\d{1,2})(?:\s*[.\-/ ]\s*(\d{2,4}))?$", s)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        if m.group(3):
            year = int(m.group(3))
            if year < 100:
                year += 1900 if year > 25 else 2000
    else:
        m = re.match(r"^(\d{1,2})\s+([а-яё]+)\s*(\d{4})?$", s)
        if m:
            day = int(m.group(1))
            key = m.group(2)[:3]
            month = MONTHS.get(key, 0)
            year = int(m.group(3)) if m.group(3) else 0

    if not (1 <= day <= 31 and 1 <= month <= 12):
        return ""
    # 31 февраля быть не может — отсекаем явную бессмыслицу.
    LONG = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    if day > LONG[month]:
        return ""
    if year and not (1920 <= year <= int(today()[:4]) - 14):
        return ""
    return "%04d-%02d-%02d" % (year or 1900, month, day)


def pretty_bday(bday):
    """1998-03-15 → 15 марта 1998. Без года — просто «15 марта»."""
    if not bday or len(bday) < 10:
        return ""
    NAMES = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
             "августа", "сентября", "октября", "ноября", "декабря"]
    y, m, d = bday[:4], int(bday[5:7]), int(bday[8:10])
    out = f"{d} {NAMES[m - 1]}"
    if y != "1900":
        out += f" {y}"
    return out


def parse_phone(text):
    """Нормализовать телефон. Пусто — если это не похоже на номер."""
    digits = "".join(ch for ch in (text or "") if ch.isdigit())
    if len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    else:
        return ""
    return "+%s (%s) %s-%s-%s" % (digits[0], digits[1:4], digits[4:7],
                                  digits[7:9], digits[9:11])


def guest_text(uid, text, g):
    st = get_state(uid)
    if not st:
        send(uid, guest_card_text(g), guest_menu(g)); return
    mode = st["mode"]
    clear_state(uid)

    if mode == "bday":
        bday = parse_bday(text)
        if not bday:
            set_state(uid, "bday")
            send(uid, "Не понял дату. Напишите как <code>15.03.1998</code> "
                         "или <code>15.03</code>.",
                    kb([[("Отмена", "g:prof")]]))
            return
        # Дату меняем только если её ещё нет — иначе подарок можно
        # было бы получать хоть каждый месяц, переставляя число.
        if g.get("bday"):
            send(uid, "Дата уже указана. Изменить её может администратор.",
                    guest_menu(g))
            return
        g2 = update(g["id"], bday=bday)
        send(uid, f"🎂 Записал: <b>{esc(pretty_bday(bday))}</b>\n\n"
                     f"В этот день начислим <b>{pts(LOYALTY['birthday'])}</b> "
                     f"бонусов.", guest_menu(g2))
        return

    if mode == "phone":
        phone = parse_phone(text)
        if not phone:
            set_state(uid, "phone")
            send(uid, "Не похоже на номер. Напишите 10 или 11 цифр, "
                         "например <code>+7 912 345-67-89</code>.",
                    kb([[("Отмена", "g:prof")]]))
            return
        g2 = update(g["id"], phone=phone)
        send(uid, f"📞 Записал: <b>{esc(phone)}</b>", guest_menu(g2))
        return

    if mode == "coupon":
        r = redeem_coupon(text.strip().upper(), g["id"], f"гость {g['card']}")
        if r.get("error"):
            set_state(uid, "coupon")          # даём ввести ещё раз
            send(uid, f"❌ {r['error']}\n\n<i>Попробуйте другой код или нажмите «Моя карта».</i>",
                    kb([[("🏠 Моя карта", "g:card")]]))
            return
        c = r["coupon"]
        if c["kind"] == "points":
            send(uid, f"✅ Купон «{esc(c['title'])}» применён!\n"
                         f"Начислено <b>{pts(c['value'])}</b> бонусов.\n"
                         f"Баланс: <b>{pts(r['guest']['bonus'])}</b>", guest_menu(r["guest"]))
        else:
            send(uid, f"✅ Купон «{esc(c['title'])}» активирован!\n\n"
                         f"Покажите это сообщение официанту.\nКод: <code>{c['code']}</code>",
                    guest_menu(g))
        for a in admin_ids():
            send(a, f"🎟 Купон {c['code']} использован · карта "
                       f"{pretty_card(g['card'])} ({esc(g['name'])})")

    elif mode == "book":
        for a in admin_ids():
            send(a, f"📅 <b>Бронь</b>\nКарта {pretty_card(g['card'])} · {esc(g['name'])}\n"
                       f"@{esc(g['username'] or '—')}\n\n{esc(text[:600])}")
        send(uid, "✅ Заявка принята. Мы свяжемся для подтверждения.", guest_menu(g))

    elif mode == "dm":
        for a in admin_ids():
            send(a, f"✉️ <b>Сообщение директору</b>\nКарта {pretty_card(g['card'])} · {esc(g['name'])}\n"
                       f"@{esc(g['username'] or '—')}\n\n{esc(text[:1500])}")
        send(uid, "✅ Отправлено. Спасибо — читаем каждое сообщение.", guest_menu(g))

# ══════════════════════════════════════════════════════════════
#  ОФИЦИАНТ
# ══════════════════════════════════════════════════════════════
def staff_menu():
    return kb([
        [("💳 Начислить по чеку", "s:pay")],
        [("🔍 Найти гостя", "s:find")],
        [("🎟 Проверить купон", "s:coup")],
        [("📊 Смена сегодня", "s:day")],
    ])

def staff_start(uid):
    send(uid,
        f"<b>Смена · {esc(BRAND['name'])}</b>\n"
        f"<i>панель официанта</i>\n\n"
        f"<b>Быстрое начисление</b>\n"
        f"Отправьте одним сообщением:\n"
        f"<code>номер_карты сумма</code>\n\n"
        f"Пример: <code>482951 2400</code>\n"
        f"Со списанием: <code>482951 2400 500</code>\n\n"
        f"Или кнопки ниже.",
        staff_menu())

def staff_cb(uid, data, cb):
    mid = cb["message"]["message_id"]
    act = data[2:]

    if act == "pay":
        set_state(uid, "s_pay")
        edit(uid, mid,
            "💳 <b>Начисление по чеку</b>\n\nОтправьте: <code>номер_карты сумма</code>\n"
            "<i>Например: 482951 2400</i>\n\n"
            "Чтобы сразу списать бонусы, добавьте третьим числом:\n"
            "<code>482951 2400 500</code>",
            kb([[("Отмена", "s:home")]]))

    elif act == "find":
        set_state(uid, "s_find")
        edit(uid, mid, "🔍 <b>Поиск гостя</b>\n\nОтправьте имя, номер карты или телефон.",
                kb([[("Отмена", "s:home")]]))

    elif act == "coup":
        set_state(uid, "s_coup")
        edit(uid, mid, "🎟 <b>Проверка купона</b>\n\nОтправьте: <code>код номер_карты</code>\n"
                          "<i>Например: X7K2M9 482951</i>",
                kb([[("Отмена", "s:home")]]))

    elif act == "day":
        s = stats()
        edit(uid, mid,
            f"<b>Сегодня</b>\n\n"
            f"🧾 Визитов: <b>{s['today_visits']}</b>\n"
            f"💵 Выручка: <b>{money(s['today_revenue'])}</b>\n"
            f"👥 Всего гостей в базе: {s['guests']}",
            kb([[("Обновить", "s:day")], [("← Меню", "s:home")]]))

    elif act == "home":
        clear_state(uid)
        edit(uid, mid, "<b>Панель официанта</b>\n\nВыберите действие:", staff_menu())

    elif act.startswith("ok:"):
        # подтверждение начисления: s:ok:gid:total:pts  (+ optional key for double-tap)
        parts = data.split(":")
        # s:ok:gid:total:pts or s:ok:gid:total:pts:key
        if len(parts) < 5:
            answer(cb["id"], "Некорректные данные", True); return
        gid, total, upts = int(parts[2]), int(parts[3]), int(parts[4])
        idk = parts[5] if len(parts) > 5 else f"bot:{uid}:{gid}:{total}:{upts}:{today()}"
        r = checkout(gid, total, upts, "", f"оф. {uid}", idempotency_key=idk)
        if r.get("error"):
            answer(cb["id"], r["error"], True); return
        g = r["guest"]
        t = (f"✅ <b>{'Повтор (уже проведено)' if r.get('replay') else 'Проведено'}</b>\n\n"
             f"Карта {pretty_card(g['card'])} · {esc(g['name'])}\n"
             f"Чек: {money(int(total))}\n")
        if int(upts):
            t += f"Списано: {pts(int(upts))} бонусов\n"
        t += f"Начислено: <b>+{pts(r['earned'] + r['extra'])}</b>\n"
        if r["why"]:
            t += f"🎉 {esc(r['why'])}\n"
        t += f"Баланс гостя: <b>{pts(g['bonus'])}</b>"
        edit(uid, mid, t, staff_menu())
        if not r.get("replay"):
            notify_guest_visit(g, r, int(total), int(upts))

def staff_text(uid, text):
    st = get_state(uid)
    mode = st["mode"] if st else None

    # Быстрый ввод «482951 2400» работает всегда.
    # Номер карты гость называет группами — «482 951», — поэтому сначала
    # пробуем склеить первые куски в существующий номер, а уже остаток
    # считать суммой. Иначе «482 951 2400» разобралось бы как карта 482.
    nums = re.findall(r"\d+", text)
    if mode in (None, "s_pay") and len(nums) >= 2 and not text.strip().startswith("/"):
        card, g, rest = None, None, []
        for take in (3, 2, 1):
            if len(nums) < take + 1:
                continue
            cand = "".join(nums[:take])
            found = get_by_card(cand)
            if found:
                card, g, rest = cand, found, nums[take:]
                break
        if g is None:
            card, rest = nums[0], nums[1:]
        if not rest:
            send(uid, "Нужна ещё сумма чека: <code>482951 2400</code>",
                    staff_menu()); return
        clear_state(uid)
        total = int(rest[0])
        upts = int(rest[1]) if len(rest) > 1 else 0
        if not g:
            send(uid, f"❌ Карта <code>{esc(card)}</code> не найдена", staff_menu()); return
        p = preview(g["id"], total, upts)
        if p.get("error"):
            send(uid, f"❌ {p['error']}", staff_menu()); return
        t = (f"<b>Проверьте перед подтверждением</b>\n\n"
             f"👤 {esc(g['name'])} · карта {pretty_card(g['card'])}\n"
             f"⭐️ {p['level']['name']} · кэшбэк {p['level']['cashback']}%\n"
             f"💰 Баланс: {pts(g['bonus'])}\n\n"
             f"🧾 Чек: <b>{money(total)}</b>\n")
        if upts:
            t += f"➖ Списать: <b>{pts(p['pay'])}</b>"
            if p["pay"] < upts:
                t += f" <i>(максимум {pts(p['max_pay'])})</i>"
            t += f"\n💵 К оплате деньгами: <b>{money(p['to_pay'])}</b>\n"
        else:
            t += f"<i>Можно списать до {pts(p['max_pay'])} бонусов</i>\n"
        t += f"➕ Начислим: <b>{pts(p['earned'])}</b>\n"
        t += f"💰 Баланс станет: <b>{pts(p['balance_after'])}</b>"
        idk = "b" + gen_code(10)
        send(uid, t, kb([
            [("✅ Подтвердить", f"s:ok:{g['id']}:{total}:{p['pay']}:{idk}")],
            [("Отмена", "s:home")]]))
        return

    if mode == "s_find":
        clear_state(uid)
        res = find(text, 10)
        if not res:
            send(uid, "Никого не нашли", staff_menu()); return
        t = f"<b>Найдено: {len(res)}</b>\n\n"
        for g in res:
            lv = level_of(g["spent"])
            t += (f"🎫 <code>{pretty_card(g['card'])}</code> · {esc(g['name'] or '—')}\n"
                  f"    {pts(g['bonus'])} бонусов · {lv['name']} · визитов {g['visits']}\n")
        send(uid, t, staff_menu())
        return

    if mode == "s_coup":
        clear_state(uid)
        parts = text.split()
        if len(parts) < 2:
            send(uid, "Нужно: <code>код номер_карты</code>", staff_menu()); return
        g = get_by_card(parts[1])
        if not g:
            send(uid, "❌ Карта не найдена", staff_menu()); return
        r = redeem_coupon(parts[0], g["id"], f"оф. {uid}")
        if r.get("error"):
            send(uid, f"❌ {r['error']}", staff_menu()); return
        c = r["coupon"]
        send(uid, f"✅ Купон «{esc(c['title'])}» применён\n"
                     f"Гость: {esc(g['name'])} · карта {pretty_card(g['card'])}",
                staff_menu())
        try:
            send(g["tg_id"], f"🎟 Купон «{esc(c['title'])}» использован в заведении.")
        except Exception:
            pass
        return

    send(uid, "Отправьте <code>номер_карты сумма</code> или выберите действие:", staff_menu())

def notify_guest_visit(g, r, total, upts):
    """Уведомление гостю после начисления."""
    if g.get("muted"):
        return
    first = (g.get("name") or "Гость").split()[0]
    t = (f"<b>Спасибо, что были в «{esc(BRAND['name'])}»!</b>\n\n"
         f"{esc(first)}, ваш визит учтён.\n\n"
         f"Чек: <b>{money(total)}</b>\n")
    if upts:
        t += f"Списано бонусов: <b>{pts(upts)}</b>\n"
    t += f"Начислено: <b>+{pts(r['earned'] + r['extra'])}</b>\n"
    if r["why"]:
        t += f"Подарок: {esc(r['why'])}\n"
    t += f"\nБаланс сейчас: <b>{pts(g['bonus'])}</b> бонусов"
    nx = next_level(g["spent"])
    if nx:
        t += f"\nДо «{esc(nx['name'])}» — ещё {money(nx['from'] - g['spent'])}"
    t += f"\n\n<i>Ждём вас снова в «{esc(BRAND['name'])}»</i>"
    try:
        send(g["tg_id"], t)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════
#  АДМИНИСТРАТОР
# ══════════════════════════════════════════════════════════════
def admin_menu(uid=None):
    rows = [
        [("Статистика", "a:stat"), ("Гости", "a:guests")],
        [("Начислить", "s:pay"), ("Найти", "a:find")],
        [("Купоны", "a:coups")],
        [("Рассылка", "a:cast")],
        [("Выгрузить CSV", "a:export")],
        [("Копия базы", "a:backup"), ("Настройки", "a:set")],
    ]
    # Раздача ролей — только владельцу. Директор не должен мочь
    # разжаловать того, кто ему бота поставил.
    if uid is not None and is_owner(uid):
        rows.insert(5, [("Роли и доступ", "a:roles")])
    return kb(rows)

def admin_start(uid):
    s = stats()
    send(uid,
        f"<b>Управление · {esc(BRAND['name'])}</b>\n"
        f"<i>директор / владелец</i>\n\n"
        f"Гостей в базе: <b>{s['guests']}</b>\n"
        f"Активны за 30 дней: <b>{s['active30']}</b>\n"
        f"Визитов всего: <b>{s['visits']}</b>\n"
        f"Выручка (учтённая): <b>{money(s['revenue'])}</b>\n"
        f"Бонусов «на руках» у гостей: <b>{pts(s['liability'])}</b>\n\n"
        f"Сегодня: {s['today_visits']} визитов · {money(s['today_revenue'])}",
        admin_menu(uid))

def admin_cb(uid, data, cb):
    mid = cb["message"]["message_id"]
    act = data[2:]

    if act == "home":
        clear_state(uid)
        s = stats()
        edit(uid, mid, f"<b>Админ-панель</b>\n\n👥 {s['guests']} гостей · "
                          f"🧾 {s['visits']} визитов", admin_menu(uid))

    elif act == "stat":
        s = stats()
        t = (f"<b>📊 Статистика</b>\n\n"
             f"<b>Сегодня</b>\n🧾 {s['today_visits']} визитов · {money(s['today_revenue'])}\n\n"
             f"<b>Всего</b>\n"
             f"👥 Гостей: {s['guests']} (активны 30 дн: {s['active30']})\n"
             f"🧾 Визитов: {s['visits']}\n"
             f"💵 Выручка: {money(s['revenue'])}\n"
             f"📈 Средний чек: {money(s['avg'])}\n\n"
             f"<b>Бонусы</b>\n"
             f"➕ Начислено всего: {pts(s['given'])}\n"
             f"➖ Потрачено гостями: {pts(s['used'])}\n"
             f"💰 На руках сейчас: <b>{pts(s['liability'])}</b>\n\n"
             f"<b>Уровни</b>\n")
        for name, n in s["levels"]:
            t += f"• {name}: {n}\n"
        if s["top"]:
            t += "\n<b>Топ позиций</b>\n"
            for i, (name, q) in enumerate(s["top"][:7], 1):
                t += f"{i}. {esc(name)} — {q}\n"
        edit(uid, mid, t, kb([[("Обновить", "a:stat")], [("← Назад", "a:home")]]))

    elif act == "guests":
        gl = all_guests()[:15]
        if not gl:
            edit(uid, mid, "Гостей пока нет", kb([[("← Назад", "a:home")]])); return
        t = f"<b>👥 Гости</b> · всего {count_guests()}\n\n"
        for g in gl:
            lv = level_of(g["spent"])
            t += (f"🎫 <code>{pretty_card(g['card'])}</code> {esc(g['name'] or '—')}\n"
                  f"    {pts(g['bonus'])} б. · {lv['name']} · "
                  f"{g['visits']} виз. · {money(g['spent'])}\n")
        t += "\n<i>Показаны 15 последних. Полный список — в выгрузке.</i>"
        edit(uid, mid, t, kb([
            [("🔍 Найти конкретного", "a:find")],
            [("📥 Выгрузить всех", "a:export")],
            [("← Назад", "a:home")]]))

    elif act == "find":
        set_state(uid, "a_find")
        edit(uid, mid, "🔍 Отправьте имя, карту, телефон или @username",
                kb([[("Отмена", "a:home")]]))

    elif act.startswith("g:"):
        gid = int(act[2:])
        show_guest_card(uid, mid, gid)

    elif act.startswith("adj:"):
        gid = int(act[4:])
        set_state(uid, "a_adj", gid=gid)
        edit(uid, mid, "Отправьте число: <code>+500</code> или <code>-200</code>\n"
                          "Можно с причиной: <code>+500 компенсация</code>",
                kb([[("Отмена", f"a:g:{gid}")]]))

    elif act.startswith("bday:"):
        gid = int(act[5:])
        set_state(uid, "a_bday", gid=gid)
        edit(uid, mid,
            "🎂 Отправьте дату: <code>15.03.1998</code> или <code>15.03</code>\n"
            "Чтобы стереть — отправьте <code>-</code>",
            kb([[("Отмена", f"a:g:{gid}")]]))

    elif act.startswith("phone:"):
        gid = int(act[6:])
        set_state(uid, "a_phone", gid=gid)
        edit(uid, mid,
            "📞 Отправьте номер: <code>+7 912 345-67-89</code>\n"
            "Чтобы стереть — отправьте <code>-</code>",
            kb([[("Отмена", f"a:g:{gid}")]]))

    elif act.startswith("blk:"):
        gid = int(act[4:])
        g = get(gid)
        update(gid, blocked=0 if g["blocked"] else 1)
        answer(cb["id"], "Карта разблокирована" if g["blocked"] else "Карта заблокирована")
        show_guest_card(uid, mid, gid)

    elif act == "coups":
        cs = list_coupons()
        t = "<b>🎟 Купоны</b>\n\n"
        if not cs:
            t += "<i>Пока не создано ни одного.</i>\n"
        for c in cs[:12]:
            state = "✅" if (c["active"] and c["uses_left"] > 0) else "⛔️"
            kind = {"points": f"+{c['value']} бонусов",
                    "percent": f"скидка {c['value']}%",
                    "gift": "подарок"}.get(c["kind"], c["kind"])
            t += (f"{state} <code>{c['code']}</code> · {esc(c['title'])}\n"
                  f"    {kind} · осталось {c['uses_left']}\n")
        edit(uid, mid, t, kb([
            [("➕ Создать купон", "a:newc")],
            [("← Назад", "a:home")]]))

    elif act == "newc":
        set_state(uid, "a_newc")
        edit(uid, mid,
            "<b>Новый купон</b>\n\nОтправьте одной строкой:\n"
            "<code>название | тип | значение | сколько_штук</code>\n\n"
            "Типы: <code>points</code> (бонусы), <code>percent</code> (скидка %), "
            "<code>gift</code> (подарок)\n\n"
            "<i>Пример: Кофе в подарок | gift | 0 | 50</i>\n"
            "<i>Пример: 500 бонусов | points | 500 | 100</i>",
            kb([[("Отмена", "a:coups")]]))

    elif act == "cast":
        n = count_guests()
        set_state(uid, "a_cast")
        edit(uid, mid,
            f"📣 <b>Рассылка</b>\n\nПолучателей: <b>{n}</b>\n\n"
            f"Отправьте текст сообщения. Поддерживается <b>HTML</b>.\n"
            f"<i>Гости, отключившие уведомления, не получат.</i>",
            kb([[("Отмена", "a:home")]]))

    elif act.startswith("castgo:"):
        text = STATE.get(uid, {}).get("data", {}).get("text")
        clear_state(uid)
        if not text:
            answer(cb["id"], "Текст потерялся, начните заново", True); return
        edit(uid, mid, "📤 Отправляю…")
        threading.Thread(target=do_broadcast, args=(uid, text), daemon=True).start()

    elif act == "export":
        answer(cb["id"], "Готовлю файлы…")
        send_doc(uid, f"гости_{today()}.csv", csv_guests(),
                    f"👥 Гости · {count_guests()} записей")
        send_doc(uid, f"визиты_{today()}.csv", csv_visits(),
                    "🧾 История визитов")
        if SHEETS_URL:
            send(uid, "☁️ Google Таблица обновляется автоматически.", admin_menu(uid))
        else:
            send(uid, "Файлы открываются в Excel и Google Таблицах.", admin_menu(uid))

    elif act == "backup":
        answer(cb["id"], "Готовлю копию…")
        sent = send_to_admins(tg, [uid], "по кнопке")
        if not sent:
            send(uid, "❌ Не получилось сделать копию базы. "
                         "Загляните в журнал бота.", admin_menu(uid))
        else:
            send(uid,
                "Копия отправлена выше. Сохраните это сообщение — "
                "по нему база восстанавливается за минуту.\n\n"
                "<b>Как восстановить:</b> перешлите мне файл <code>.db</code>, "
                "я проверю его и спрошу подтверждение.",
                admin_menu(uid))

    elif act == "restore_yes":
        path = (get_state(uid) or {}).get("data", {}).get("path", "")
        clear_state(uid)
        if not path:
            edit(uid, mid, "Файл уже не доступен, пришлите заново.", admin_menu(uid))
        else:
            ok, why = restore(path)
            try:
                import os as _os
                _os.remove(path)
            except OSError:
                pass
            if ok:
                s = stats()
                edit(uid, mid,
                    f"✅ <b>База восстановлена</b>\n\n"
                    f"👥 Гостей: {s['guests']}\n🧾 Визитов: {s['visits']}\n\n"
                    f"Прежняя база сохранена рядом с пометкой времени — "
                    f"если восстановили не то, скажите, верну обратно.")
                send(uid, "Админ-панель", admin_menu(uid))
                log(f"База восстановлена админом {uid}")
            else:
                edit(uid, mid, f"❌ Не вышло: {esc(why)}", admin_menu(uid))

    elif act == "restore_no":
        path = (get_state(uid) or {}).get("data", {}).get("path", "")
        clear_state(uid)
        if path:
            try:
                import os as _os
                _os.remove(path)
            except OSError:
                pass
        edit(uid, mid, "Отменено. База осталась прежней.", admin_menu(uid))

    elif act == "roles":
        if not is_owner(uid):
            answer(cb["id"], "Раздел недоступен", True); return
        show_roles(uid, mid)

    elif act.startswith("addrole:"):
        if not is_owner(uid):
            answer(cb["id"], "Раздел недоступен", True); return
        want = act.split(":")[1]
        set_state(uid, "a_addrole", want=want)
        name = ROLE_NAMES.get(want, want)
        edit(uid, mid,
            f"<b>Кому выдать роль «{name}»?</b>\n\n"
            f"Подойдёт любое из трёх:\n\n"
            f"1️⃣ <b>@логин</b> — можно несколько через пробел\n"
            f"2️⃣ <b>Переслать</b> мне любое сообщение этого человека — "
            f"номер возьму сам\n"
            f"3️⃣ <b>Число</b> — если человек пришлёт вам ответ на "
            f"команду <code>/id</code>\n\n"
            f"<i>Если человек уже писал боту, номер подтянется сразу. "
            f"Если нет — роль запишется и включится при его первом входе.</i>",
            kb([[("Отмена", "a:roles")]]))

    elif act == "linkroles":
        if not is_owner(uid):
            answer(cb["id"], "Раздел недоступен", True); return
        linked = link_pending_roles()
        for r in linked:
            _notify_role(r["tg_id"], r["role"])
        answer(cb["id"],
                  f"Найдено номеров: {len(linked)}" if linked
                  else "Никого не нашли — эти люди боту ещё не писали", True)
        show_roles(uid, mid)

    elif act.startswith("delrole:"):
        if not is_owner(uid):
            answer(cb["id"], "Раздел недоступен", True); return
        rid = int(act.split(":")[1])
        row = next((r for r in list_roles() if r["id"] == rid), None)
        if not row:
            show_roles(uid, mid); return
        who = ("@" + row["username"]) if row["username"] else f"ID {row['tg_id']}"
        edit(uid, mid,
            f"Снять роль «{ROLE_NAMES.get(row['role'], row['role'])}» "
            f"у <b>{esc(who)}</b>?\n\n"
            f"Человек станет обычным гостем. Его карта и бонусы останутся.",
            kb([[("Снять", f"a:delrole_ok:{rid}")], [("Отмена", "a:roles")]]))

    elif act.startswith("delrole_ok:"):
        if not is_owner(uid):
            answer(cb["id"], "Раздел недоступен", True); return
        rid = int(act.split(":")[1])
        ok, why = revoke(rid, by=f"владелец {uid}")
        answer(cb["id"], why if ok else why, not ok)
        show_roles(uid, mid)

    elif act == "set":
        t = (f"<b>⚙️ Настройки</b>\n\n"
             f"Кэшбэк: {LOYALTY['cashback']}%\n"
             f"Оплата бонусами: до {LOYALTY['max_pay_percent']}% чека\n"
             f"Приветственные: {LOYALTY['welcome']}\n"
             f"За второй визит: {LOYALTY['second_visit']}\n"
             f"День рождения: {LOYALTY['birthday']}\n"
             f"Сгорание: {LOYALTY['burn_days'] or 'выключено'} дней\n\n"
             f"Владельцев: {len(list_roles('owner'))} · "
             f"директоров: {len(list_roles('admin'))} · "
             f"официантов: {len(list_roles('staff'))}\n"
             f"Google Таблица: {'подключена' if SHEETS_URL else 'не подключена'}\n\n"
             f"<i>Меняется в файле py</i>")
        edit(uid, mid, t, kb([[("← Назад", "a:home")]]))

def _notify_role(tg_id, want):
    """Сообщить человеку, что ему выдали роль. Молча, если не открывал бота."""
    texts = {
        "owner": "👑 Вам выдана роль <b>владельца</b> бота.\n\n"
                 "Доступна вся админка и раздача ролей.",
        "admin": "🎩 Вам выдана роль <b>директора</b>.\n\n"
                 "Доступна статистика, база гостей, купоны, рассылки и выгрузка.",
        "staff": "🧑‍🍳 Вам выдана роль <b>официанта</b>.\n\n"
                 "Теперь можно принимать чеки: пришлите номер карты и сумму, "
                 "например <code>482951 2400</code>.",
    }
    try:
        send(tg_id, texts.get(want, "Вам выдана новая роль.") +
                       "\n\nНажмите /start, чтобы обновить меню.")
    except Exception:
        pass


def show_roles(uid, mid=None):
    """Экран управления ролями. Виден только владельцу."""
    rows = list_roles()
    t = "<b>🔑 Роли и доступ</b>\n\n"
    if not rows:
        t += "Пока никого нет.\n"
    pending = 0
    for r in rows:
        who = ("@" + r["username"]) if r["username"] else f"ID {r['tg_id']}"
        if r["tg_id"]:
            mark = f"  <code>{r['tg_id']}</code>"
        else:
            mark = "  <i>(номер пока не найден)</i>"
            pending += 1
        t += f"{'👑' if r['role']=='owner' else '🎩' if r['role']=='admin' else '🧑‍🍳'} " \
             f"<b>{ROLE_NAMES.get(r['role'], r['role'])}</b> — {esc(who)}{mark}\n"
    if pending:
        t += (f"\n⏳ У {pending} чел. номер ещё не найден — роль включится "
              f"при первом входе в бота. Ускорить: перешлите мне любое "
              f"их сообщение.\n")
    t += ("\n<b>Кто что видит</b>\n"
          "👑 Владелец — всё, включая этот раздел\n"
          "🎩 Директор — вся админка, кроме раздачи ролей\n"
          "🧑‍🍳 Официант — только приём чеков\n"
          "Гость — только свою карту, админки не видит вовсе")

    kb_rows = [
        [("➕ Директор", "a:addrole:admin"), ("➕ Официант", "a:addrole:staff")],
        [("➕ Ещё владелец", "a:addrole:owner")],
    ]
    if pending:
        kb_rows.append([("🔗 Найти номера", "a:linkroles")])
    for r in rows:
        who = ("@" + r["username"]) if r["username"] else str(r["tg_id"])
        kb_rows.append([(f"✖️ {ROLE_NAMES.get(r['role'], r['role'])} · {who}",
                         f"a:delrole:{r['id']}")])
    kb_rows.append([("← Назад", "a:home")])

    if mid:
        edit(uid, mid, t, kb(kb_rows))
    else:
        send(uid, t, kb(kb_rows))


def show_guest_card_msg(uid, gid):
    """Карточка гостя новым сообщением — после правки из переписки."""
    m = send(uid, "…")
    if m:
        show_guest_card(uid, m["message_id"], gid)


def show_guest_card(uid, mid, gid):
    g = get(gid)
    if not g:
        edit(uid, mid, "Гость не найден", admin_menu(uid)); return
    lv = level_of(g["spent"])
    fav = favourites(gid, 5)
    t = (f"🎫 <b>Карта {pretty_card(g['card'])}</b>\n\n"
         f"👤 {esc(g['name'] or '—')}"
         + (f" · @{esc(g['username'])}" if g["username"] else "") + "\n"
         f"📞 {esc(g['phone'] or '—')}\n"
         f"🎂 {esc(pretty_bday(g['bday']) or '—')}\n\n"
         f"⭐️ {lv['name']} · кэшбэк {lv['cashback']}%\n"
         f"💰 Бонусов: <b>{pts(g['bonus'])}</b>\n"
         f"🧾 Визитов: {g['visits']} · на {money(g['spent'])}\n"
         f"🕐 Последний: {(g['last_visit'] or '—')[:16]}\n")
    if g["blocked"]:
        t += "\n⛔️ <b>Карта заблокирована</b>\n"
    if fav:
        t += "\n<b>Обычно берёт:</b>\n" + "\n".join(f"• {esc(n)} ×{q}" for n, q in fav) + "\n"
    h = history(gid, 5)
    if h:
        t += "\n<b>Последнее:</b>\n"
        for v in h:
            when = (v["at"] or "")[:16]
            if v["type"] == "visit":
                t += f"• {when} — {money(v['total'])} · +{pts(v['earned'])}\n"
            elif v["type"] == "adjust":
                t += f"• {when} — правка · {esc(v['extra_why'])}\n"
            else:
                t += f"• {when} — регистрация\n"
    edit(uid, mid, t, kb([
        [("💰 Изменить баланс", f"a:adj:{gid}")],
        [("🎂 День рождения", f"a:bday:{gid}"), ("📞 Телефон", f"a:phone:{gid}")],
        [("⛔️ Разблокировать" if g["blocked"] else "⛔️ Заблокировать", f"a:blk:{gid}")],
        [("← К списку", "a:guests")]]))

def admin_text(uid, text):
    st = get_state(uid)
    mode = st["mode"] if st else None

    if mode == "a_find":
        clear_state(uid)
        res = find(text, 10)
        if not res:
            send(uid, "Никого не нашли", admin_menu(uid)); return
        rows = [[(f"{pretty_card(g['card'])} · {g['name'] or '—'} · {pts(g['bonus'])}б",
                  f"a:g:{g['id']}")]
                for g in res]
        rows.append([("← Назад", "a:home")])
        send(uid, f"Найдено: {len(res)}", kb(rows))
        return

    if mode == "a_adj":
        gid = st["data"]["gid"]
        clear_state(uid)
        m = re.match(r"\s*([+-]?\d+)\s*(.*)", text)
        if not m:
            send(uid, "Нужно число: <code>+500</code> или <code>-200</code>", admin_menu(uid)); return
        delta = int(m.group(1)); why = m.group(2).strip() or "правка администратора"
        r = adjust(gid, delta, why, f"админ {uid}")
        if r.get("error"):
            send(uid, f"❌ {r['error']}", admin_menu(uid)); return
        g = r["guest"]
        send(uid, f"✅ Баланс карты {pretty_card(g['card'])}: "
                     f"<b>{pts(g['bonus'])}</b>", admin_menu(uid))
        if not g.get("muted"):
            sign = "начислено" if delta > 0 else "списано"
            try:
                send(g["tg_id"], f"💰 Вам {sign} <b>{pts(abs(delta))}</b> бонусов\n"
                                    f"<i>{esc(why)}</i>\n\nБаланс: <b>{pts(g['bonus'])}</b>")
            except Exception:
                pass
        return

    if mode == "a_addrole":
        want = st["data"]["want"]
        clear_state(uid)
        if not is_owner(uid):
            send(uid, "Раздел недоступен", admin_menu(uid)); return
        parts = [p for p in re.split(r"[\s,;]+", text) if p.strip()]
        added, waiting, bad = [], [], []
        for p in parts:
            if p.lstrip("-").isdigit():
                r = grant(want, tg_id=int(p), by=f"владелец {uid}")
                if r:
                    added.append(f"ID {p}")
                    _notify_role(int(p), want)
                else:
                    bad.append(p)
                continue
            u = norm_username(p)
            if not u:
                bad.append(p); continue
            r = grant(want, username=u, by=f"владелец {uid}")
            if not r:
                bad.append(p); continue
            if r.get("tg_id"):
                # ID нашёлся сам — человек уже писал боту.
                added.append("@" + u)
                _notify_role(r["tg_id"], want)
            else:
                waiting.append("@" + u)
        name = ROLE_NAMES.get(want, want)
        msg_t = ""
        if added:
            msg_t += (f"✅ Роль «{name}» выдана и уже действует:\n"
                      + "\n".join("• " + esc(a) for a in added))
        if waiting:
            msg_t += ("\n\n" if msg_t else "") + \
                     f"⏳ Роль «{name}» записана, ждём первого входа:\n" + \
                     "\n".join("• " + esc(w) for w in waiting) + \
                     "\n\n<i>Эти люди боту ещё не писали, поэтому его номер " \
                     "пока неизвестен. Как только напишут /start — роль " \
                     "включится сама.</i>\n" \
                     "Хотите включить прямо сейчас — перешлите мне любое " \
                     "сообщение этого человека."
        if bad:
            msg_t += ("\n\n" if msg_t else "") + "❌ Не понял:\n" + \
                     "\n".join("• " + esc(b) for b in bad) + \
                     "\n<i>Логин пишется как @name, либо пришлите число из /id</i>"
        send(uid, msg_t or "Ничего не добавлено")
        show_roles(uid)
        return

    if mode == "a_bday":
        gid = st["data"]["gid"]
        clear_state(uid)
        if text.strip() in ("-", "—"):
            update(gid, bday="")
            send(uid, "🎂 Дата стёрта")
        else:
            bday = parse_bday(text)
            if not bday:
                send(uid, "Не понял дату. Нужно <code>15.03.1998</code>",
                        admin_menu(uid)); return
            update(gid, bday=bday)
            send(uid, f"🎂 Записано: <b>{esc(pretty_bday(bday))}</b>")
        show_guest_card_msg(uid, gid)
        return

    if mode == "a_phone":
        gid = st["data"]["gid"]
        clear_state(uid)
        if text.strip() in ("-", "—"):
            update(gid, phone="")
            send(uid, "📞 Телефон стёрт")
        else:
            phone = parse_phone(text)
            if not phone:
                send(uid, "Не похоже на номер. Нужно 10 или 11 цифр.",
                        admin_menu(uid)); return
            update(gid, phone=phone)
            send(uid, f"📞 Записано: <b>{esc(phone)}</b>")
        show_guest_card_msg(uid, gid)
        return

    if mode == "a_newc":
        clear_state(uid)
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 4:
            send(uid, "Формат: <code>название | тип | значение | штук</code>", admin_menu(uid)); return
        title, kind, val, uses = parts[0], parts[1].lower(), parts[2], parts[3]
        if kind not in ("points", "percent", "gift"):
            send(uid, "Тип: points, percent или gift", admin_menu(uid)); return
        try:
            val = int(val); uses = int(uses)
        except ValueError:
            send(uid, "Значение и количество — числа", admin_menu(uid)); return
        c = add_coupon(title, kind, val, uses=uses)
        send(uid, f"✅ Купон создан\n\n<code>{c['code']}</code> · {esc(c['title'])}\n"
                     f"Тираж: {c['uses_left']}\n\n"
                     f"<i>Гость вводит код в разделе «Ввести купон»</i>", admin_menu(uid))
        return

    if mode == "a_cast":
        set_state(uid, "a_cast_ok", text=text)
        n = count_guests()
        send(uid, f"<b>Предпросмотр:</b>\n\n{text}\n\n"
                     f"—————\nОтправить <b>{n}</b> гостям?",
                kb([[("📤 Отправить", "a:castgo:1")], [("Отмена", "a:home")]]))
        return

    # по умолчанию — как у официанта (быстрый ввод чека)
    staff_text(uid, text)

def do_broadcast(admin_id, text):
    sent = failed = muted = 0
    for g in all_guests():
        if g.get("muted"):
            muted += 1; continue
        if not g.get("tg_id"):
            continue
        r = send(g["tg_id"], text)
        if r:
            sent += 1
        else:
            failed += 1
        time.sleep(0.05)          # ~20 сообщений в секунду, лимит Telegram
    send(admin_id, f"📣 <b>Рассылка завершена</b>\n\n"
                      f"✅ Доставлено: {sent}\n"
                      f"❌ Не дошло: {failed}\n"
                      f"🔕 Отключили уведомления: {muted}", admin_menu(admin_id))

# ══════════════════════════════════════════════════════════════
#  МАРШРУТИЗАЦИЯ
# ══════════════════════════════════════════════════════════════
def on_document(uid, doc):
    """Админ прислал файл. Ждём только базу .db для восстановления."""
    import os, tempfile
    name = doc.get("file_name") or "файл"
    if not name.lower().endswith(".db"):
        send(uid, "Я принимаю только файл базы с расширением "
                     "<code>.db</code> — тот, что присылаю в резервных копиях.")
        return
    if (doc.get("file_size") or 0) > MAX_DB_BYTES:
        send(uid, "Файл слишком большой.")
        return

    send(uid, "Проверяю файл…")
    data = download(doc["file_id"])
    if not data:
        send(uid, "❌ Не удалось скачать файл. Попробуйте прислать заново.")
        return

    fd, path = tempfile.mkstemp(suffix=".db", prefix="restore-")
    with os.fdopen(fd, "wb") as f:
        f.write(data)

    ok, why, info = check_db_file(path)
    if not ok:
        try:
            os.remove(path)
        except OSError:
            pass
        send(uid, f"❌ Файл не подходит: {esc(why)}")
        return

    cur = stats()
    set_state(uid, "restore", path=path)
    send(uid,
        f"⚠️ <b>Заменить базу?</b>\n\n"
        f"<b>В присланном файле</b>\n"
        f"👥 {info['guests']} гостей · 🧾 {info['visits']} визитов\n\n"
        f"<b>Сейчас в боте</b>\n"
        f"👥 {cur['guests']} гостей · 🧾 {cur['visits']} визитов\n\n"
        f"Текущие данные будут заменены. Старая база сохранится рядом — "
        f"откатиться можно.",
        kb([[("✅ Заменить", "a:restore_yes")],
               [("Отмена", "a:restore_no")]]))


def on_forward(uid, fwd):
    """Владелец переслал сообщение человека — вытаскиваем его ID.

    Единственный законный способ узнать чужой ID, не спрашивая человека:
    в пересланном сообщении Telegram сам указывает автора. Работает,
    только если у автора не скрыт аккаунт в настройках приватности.

    Возвращает True, если сообщение обработано как пересылка.
    """
    who_id = fwd.get("id")
    who_name = fwd.get("username", "") or ""
    if not who_id:
        return False

    # Ждали логин для роли — используем пересылку вместо него.
    st = get_state(uid)
    if st and st["mode"] == "a_addrole":
        want = st["data"]["want"]
        clear_state(uid)
        r = grant(want, username=who_name, tg_id=who_id, by=f"владелец {uid}")
        name = ROLE_NAMES.get(want, want)
        who = ("@" + who_name) if who_name else (fwd.get("first_name") or f"ID {who_id}")
        if r:
            _notify_role(who_id, want)
            send(uid, f"✅ Роль «{name}» выдана и уже действует:\n"
                         f"• {esc(who)} · <code>{who_id}</code>")
        else:
            send(uid, "Не получилось выдать роль.")
        show_roles(uid)
        return True

    # Просто пересылка — подсказываем ID и связываем висящие роли.
    linked = link_pending_roles()
    if who_name:
        row = get_role_row(username=who_name)
        if row and not row["tg_id"]:
            grant(row["role"], username=who_name, tg_id=who_id, by=f"владелец {uid}")
            _notify_role(who_id, row["role"])
            send(uid,
                f"🔗 Связал <b>@{esc(who_name)}</b> с номером <code>{who_id}</code>.\n"
                f"Роль «{ROLE_NAMES.get(row['role'], row['role'])}» теперь действует.")
            show_roles(uid)
            return True

    who = ("@" + who_name) if who_name else (fwd.get("first_name") or "этот человек")
    send(uid,
        f"Telegram ID: <code>{who_id}</code>\n"
        f"{esc(who)}\n\n"
        f"<i>Можно использовать при выдаче роли.</i>"
        + (f"\n\nЗаодно связал {len(linked)} ожидавших ролей." if linked else ""),
        admin_menu(uid))
    return True


def on_message(msg):
    uid = msg["from"]["id"]
    text = (msg.get("text") or "").strip()
    LAST_SEEN[uid] = time.time()
    uname = msg["from"].get("username", "") or ""
    if uname:
        USERNAMES[uid] = uname
        remember_username(uid, uname)
    r = role(uid, uname)

    # Владелец переслал чужое сообщение — берём ID отправителя оттуда.
    fwd = msg.get("forward_from")
    if fwd and is_owner(uid):
        if on_forward(uid, fwd):
            return

    if msg.get("document"):
        if r == "admin":
            on_document(uid, msg["document"])
        # Гостю и официанту файлы не нужны — молча пропускаем.
        return

    if text.startswith("/start"):
        clear_state(uid)
        # deep-link: /start c482951 or /start c_482951 — staff opens guest by card
        payload = text[6:].strip()  # after "/start"
        m_card = re.match(r"^c_?(\d{6})$", payload, re.I) if payload else None
        if m_card and r in ("admin", "staff"):
            g = get_by_card(m_card.group(1))
            if g:
                if r == "admin":
                    show_guest_card_msg(uid, g["id"])
                else:
                    send(uid,
                        f"👤 {esc(g['name'] or 'Гость')} · карта <code>{pretty_card(g['card'])}</code>\n"
                        f"💰 {pts(g['bonus'])} бонусов · визитов {g['visits']}\n\n"
                        f"Начислить: <code>{g['card']} сумма</code>",
                        staff_menu())
            else:
                send(uid, f"❌ Карта <code>{esc(m_card.group(1))}</code> не найдена",
                     staff_menu() if r == "staff" else admin_menu(uid))
            return
        if r == "admin":
            admin_start(uid)
        elif r == "staff":
            staff_start(uid)
        else:
            guest_start(uid, msg)
        return

    if text == "/id":
        send(uid, f"Ваш Telegram ID: <code>{uid}</code>")
        return

    if text.startswith("/stop"):
        g = get_by_tg(uid)
        if g:
            update(g["id"], muted=1)
            send(uid, "🔕 Уведомления отключены. Включить: /start")
        return

    if r == "admin":
        admin_text(uid, text)
    elif r == "staff":
        staff_text(uid, text)
    else:
        g = get_by_tg(uid) or add_guest(uid, msg["from"].get("first_name", ""),
                                              msg["from"].get("username", ""))[0]
        guest_text(uid, text, g)

def on_callback(cb):
    uid = cb["from"]["id"]
    data = cb.get("data", "")
    uname = cb["from"].get("username", "") or ""
    if uname:
        USERNAMES[uid] = uname
    r = role(uid, uname)

    # ── защита: чужие разделы недоступны ──
    if data.startswith("a:") and r != "admin":
        answer(cb["id"], "Раздел недоступен", True); return
    if data.startswith("s:") and r == "guest":
        answer(cb["id"], "Раздел недоступен", True); return

    answer(cb["id"])
    try:
        if data.startswith("g:"):
            g = get_by_tg(uid)
            if not g:
                g, _ = add_guest(uid, cb["from"].get("first_name", ""),
                                    cb["from"].get("username", ""))
            guest_cb(uid, data, cb, g)
        elif data.startswith("s:"):
            staff_cb(uid, data, cb)
        elif data.startswith("a:"):
            admin_cb(uid, data, cb)
    except Exception as e:
        log("Ошибка callback:", data, repr(e))
        log(traceback.format_exc()[:800])

# ══════════════════════════════════════════════════════════════
#  ФОНОВЫЕ ЗАДАЧИ
# ══════════════════════════════════════════════════════════════
def sheets_worker():
    """Отправка накопленных изменений в Google Таблицу."""
    import urllib.request
    while True:
        try:
            if SHEETS_URL:
                batch = take_queue(20)
                if batch:
                    ok_ids = []
                    for row in batch:
                        try:
                            req = urllib.request.Request(
                                SHEETS_URL,
                                data=row["payload"].encode("utf-8"),
                                headers={"Content-Type": "application/json"})
                            with urllib.request.urlopen(req, timeout=30) as r:
                                r.read()
                            ok_ids.append(row["id"])
                        except Exception:
                            bump_queue(row["id"])
                    drop_queue(ok_ids)
        except Exception as e:
            log("Очередь таблицы:", repr(e))
        time.sleep(8)

def daily_worker():
    """Раз в сутки: сгорание бонусов и поздравления с днём рождения."""
    last = ""
    while True:
        try:
            t = today()
            if t != last:
                last = t
                # день рождения
                for g in all_guests():
                    if g.get("muted") or not g.get("bday") or len(g["bday"]) < 10:
                        continue
                    if g["bday"][5:10] == t[5:10]:
                        try:
                            send(g["tg_id"],
                                f"🎂 <b>С днём рождения, {esc(g['name'] or 'дорогой гость')}!</b>\n\n"
                                f"Дарим <b>{pts(LOYALTY['birthday'])}</b> бонусов — "
                                f"они начислятся при следующем визите.\n\n"
                                f"Ждём вас в «{esc(BRAND['name'])}» 🖤")
                        except Exception:
                            pass
                # сгорание
                burned = burn_expired()
                if burned:
                    for a in admin_ids():
                        send(a, f"🔥 Сгорели бонусы у {len(burned)} гостей "
                                   f"(нет визитов {LOYALTY['burn_days']} дней)")
        except Exception as e:
            log("Ежедневные задачи:", repr(e))
        time.sleep(3600)

# ══════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════
def main():
    global BOT_NAME
    if not TOKEN or "ВСТАВЬ" in TOKEN:
        print("\n❌ Не указан токен бота.\n"
              "   Откройте py и вставьте токен от @BotFather\n"
              "   или задайте переменную окружения BOT_TOKEN.\n")
        return

    conn()
    me = call("getMe")
    if not me:
        print("\n❌ Telegram не отвечает или токен неверный.\n"
              "   Проверьте токен и интернет.\n")
        return
    BOT_NAME = me.get("username", "")
    log(f"Бот @{BOT_NAME} запущен")

    n = seed_roles(OWNERS, ADMINS, STAFF)
    if n:
        log(f"Роли заведены из настроек: {n}")
    roles = list_roles()
    for r in roles:
        who = ("@" + r["username"]) if r["username"] else f"ID {r['tg_id']}"
        log(f"  {ROLE_NAMES.get(r['role'], r['role'])}: {who}"
            + ("" if r["tg_id"] else "  (ещё не заходил)"))
    if not roles:
        log("⚠️  Ролей нет — админку никто не увидит.")
        log("    Впишите свой @логин в OWNERS и перезапустите.")

    if SHEETS_URL:
        log("Google Таблица подключена")
    else:
        log("Google Таблица: выкл (SHEETS_URL пуст) — CSV + бэкап в TG")

    if WEBAPP_URL:
        log(f"Mini App URL: {WEBAPP_URL}")
    else:
        log("Mini App: WEBAPP_URL не задан — кнопка WebApp скрыта")

    # HTTP API + static Mini App (stdlib)
    try:
        import web_api
        web_api.bind(sys.modules[__name__])
        if API_PORT:
            web_api.start_background(API_HOST, API_PORT)
            log(f"HTTP API: {API_HOST}:{API_PORT}  ( /api/health , /app/ )")
            log(f"  PORT env={os.environ.get('PORT')!r} API_PORT env={os.environ.get('API_PORT')!r}")
            log(f"  Проверка снаружи: https://<домен>/api/health")
    except Exception as e:
        log("HTTP API не стартовал:", repr(e))

    threading.Thread(target=sheets_worker, daemon=True).start()
    threading.Thread(target=daily_worker, daemon=True).start()
    if BACKUP_ENABLED:
        threading.Thread(target=worker,
                         args=(tg, BACKUP_HOUR, admin_ids),
                         daemon=True).start()
        log(f"Резервные копии базы включены (ежедневно в {BACKUP_HOUR}:00)")
        # Предупреждение о пустой базе: типичный признак того, что хостинг
        # стёр файл при пересборке и данные надо восстановить из копии.
        if count_guests() == 0:
            for a in admin_ids():
                send(a,
                    "⚠️ <b>База пустая</b>\n\n"
                    "Если это первый запуск — всё в порядке.\n"
                    "Если бот уже работал, значит хостинг стёр файл базы. "
                    "Найдите последнее сообщение с файлом <code>.db</code> "
                    "и перешлите его мне — я всё верну.")

    call("setMyCommands", commands=[
        {"command": "start", "description": "Карта лояльности «Исповедь»"},
        {"command": "card",  "description": "Открыть приложение"},
        {"command": "stop",  "description": "Выключить уведомления о визитах"},
    ])
    if WEBAPP_URL:
        try:
            call("setChatMenuButton", menu_button={
                "type": "web_app",
                "text": "Карта",
                "web_app": {"url": WEBAPP_URL},
            })
        except Exception as e:
            log("menu button:", repr(e))

    offset = 0
    while True:
        try:
            ups = call("getUpdates", offset=offset, timeout=50,
                          allowed_updates=["message", "callback_query"])
            if not ups:
                continue
            for u in ups:
                offset = u["update_id"] + 1
                try:
                    if "message" in u and u["message"].get("from"):
                        on_message(u["message"])
                    elif "callback_query" in u:
                        on_callback(u["callback_query"])
                except Exception as e:
                    log("Ошибка обработки:", repr(e))
                    log(traceback.format_exc()[:600])
        except KeyboardInterrupt:
            log("Остановлен вручную")
            break
        except Exception as e:
            log("Цикл:", repr(e))
            time.sleep(3)

if __name__ == "__main__":
    main()

