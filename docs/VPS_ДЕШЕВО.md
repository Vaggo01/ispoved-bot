# Исповедь на дешёвом VPS (вариант B) — без мучений Bothost

Один сервер = бот + Mini App + HTTPS.  
**Без покупки домена** (через `IP.sslip.io`).

---

## Сколько стоит (ориентир 2026)

| Площадка | От ~ | Зачем брать |
|----------|------|-------------|
| **[VDSina](https://vdsina.ru)** | **~150 ₽/мес** | Дёшево, РФ, нормально для бота |
| **[SprintHost](https://sprinthost.ru)** | **~90–150 ₽** | Ультрабюджет |
| **[FirstVDS](https://firstvds.ru)** | **~200–300 ₽** | Стабильнее, проще панель |
| **[Beget VPS](https://beget.com/ru/vps)** | **~300–500 ₽** | Удобно, поддержка по-русски |
| **[Timeweb Cloud](https://timeweb.cloud)** | **~200+ ₽** | Крупный, надёжный |

**Рекомендация при малом бюджете:**  
1) **VDSina** или **SprintHost** — минимальный тариф **1 vCPU / 1 GB RAM / Ubuntu 22.04**.  
2) Домен **не покупай** — будет `ТВОЙ_IP.sslip.io` (бесплатно + HTTPS).

Хватит: **1 GB RAM**, 10–20 GB диск. Не бери Windows.

---

## Что купить (чеклист в магазине VPS)

- [ ] Ubuntu **22.04** или **24.04**
- [ ] Публичный **IPv4**
- [ ] Регион: **Москва / СПб** (для РФ)
- [ ] Root-пароль или SSH-ключ — сохрани

После оплаты тебе дадут: **IP**, логин `root`, пароль.

---

## Установка (ты делаешь 3 действия)

### 1. Зайди на сервер

С Windows (PowerShell):

```text
ssh root@ТВОЙ_IP
```

(вставь IP с письма VPS)

### 2. Одной командой поставь всё

```bash
curl -fsSL https://raw.githubusercontent.com/Vaggo01/ispoved-bot/main/deploy/install.sh -o install.sh
bash install.sh
```

Скрипт спросит:

1. **BOT_TOKEN** — токен бота  
2. **OWNERS** — `@vagdar1` (можно Enter)  
3. **DOMAIN** — Enter = автоматически `IP.sslip.io`

### 3. Bothost — **останови** старого бота  
Иначе два процесса на один токен.

### 4. BotFather

- Domain: то, что выдал скрипт (например `185.x.x.x.sslip.io`)  
- Menu URL: `https://185.x.x.x.sslip.io/app/`

### 5. Проверка

```text
https://IP.sslip.io/api/health
https://IP.sslip.io/app/
```

Telegram → `/start` → Карта.

---

## Если curl install не сработал

```bash
apt update && apt install -y git
git clone https://github.com/Vaggo01/ispoved-bot.git /opt/ispoved
cd /opt/ispoved/deploy
cp .env.example .env
nano .env
# заполни BOT_TOKEN, DOMAIN=IP.sslip.io, WEBAPP_URL=https://IP.sslip.io/app/
bash ../deploy/install.sh
# или:
docker compose up -d --build
```

---

## Полезные команды

```bash
cd /opt/ispoved/deploy
docker compose logs -f bot      # логи
docker compose restart bot      # рестарт
docker compose pull && docker compose up -d --build   # обновление из git
```

Обновление кода:

```bash
cd /opt/ispoved && git pull
cd deploy && docker compose up -d --build
```

---

## Свой красивый домен (позже, не обязательно)

Купить `ispoved-perm.ru` (~200 ₽/год) → A-запись на IP VPS →  
в `.env` `DOMAIN=ispoved-perm.ru` → `docker compose up -d`  
Caddy сам выпустит SSL.

Для сдачи клиенту **sslip.io достаточно** — внутри Telegram URL почти не видно.

---

## Деньги (честно)

| | |
|--|--|
| VPS | ~150–300 ₽/мес |
| Домен | 0 ₽ (sslip) |
| Bothost | можно не платить / отключить бота |

Клиенту: «бот + приложение 24/7 на отдельном сервере» — звучит солидно.

---

## Если совсем нет денег на VPS

Временно сдаём **только чат-бота** на Bothost (без Mini App).  
Mini App — как только будет ~200 ₽ на VPS.
