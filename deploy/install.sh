#!/usr/bin/env bash
# Установка Исповеди на чистый Ubuntu/Debian VPS (1 команда).
# Запуск:  bash install.sh
set -euo pipefail

echo "=== Исповедь · установка на VPS ==="

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Запусти от root:  sudo bash install.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git

# Docker
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

# Compose plugin
if ! docker compose version >/dev/null 2>&1; then
  apt-get install -y docker-compose-plugin || true
fi

# Репо
APP_DIR=/opt/ispoved
if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone https://github.com/Vaggo01/ispoved-bot.git "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only || true
fi
cd "$APP_DIR/deploy"

# IP сервера
IP=$(curl -4 -fsS ifconfig.me || curl -4 -fsS icanhazip.com || true)
IP=$(echo "$IP" | tr -d '[:space:]')
DEFAULT_DOMAIN="${IP}.sslip.io"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ""
  echo "--- Настройка (Enter = значение по умолчанию) ---"
  read -r -p "BOT_TOKEN: " BOT_TOKEN
  read -r -p "OWNERS [@vagdar1]: " OWNERS
  OWNERS=${OWNERS:-@vagdar1}
  read -r -p "DOMAIN [${DEFAULT_DOMAIN}]: " DOMAIN
  DOMAIN=${DOMAIN:-$DEFAULT_DOMAIN}

  sed -i "s|^BOT_TOKEN=.*|BOT_TOKEN=${BOT_TOKEN}|" .env
  sed -i "s|^OWNERS=.*|OWNERS=${OWNERS}|" .env
  sed -i "s|^DOMAIN=.*|DOMAIN=${DOMAIN}|" .env
  sed -i "s|^WEBAPP_URL=.*|WEBAPP_URL=https://${DOMAIN}/app/|" .env
fi

echo ""
echo "Собираю и запускаю..."
docker compose pull caddy || true
docker compose build --no-cache bot
docker compose up -d

# Ждём health
sleep 3
DOMAIN_VAL=$(grep '^DOMAIN=' .env | cut -d= -f2- | tr -d '\r')
WEBAPP=$(grep '^WEBAPP_URL=' .env | cut -d= -f2- | tr -d '\r')

echo ""
echo "=== Готово ==="
echo "API:     https://${DOMAIN_VAL}/api/health"
echo "MiniApp: ${WEBAPP}"
echo ""
echo "Проверка через 20–40 сек (SSL):"
echo "  curl -s https://${DOMAIN_VAL}/api/health"
echo ""
echo "BotFather:"
echo "  Domain:  ${DOMAIN_VAL}"
echo "  Menu:    ${WEBAPP}"
echo ""
echo "Логи:  cd /opt/ispoved/deploy && docker compose logs -f bot"
echo "Стоп:  docker compose down"
echo "Bothost можно ВЫКЛЮЧИТЬ (один токен = один бот)."
