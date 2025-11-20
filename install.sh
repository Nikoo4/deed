#!/bin/bash
set -euo pipefail

# Репозиторий с сервером
REPO="https://github.com/Nikoo4/deed.git"
APP_DIR="/opt/roulette-tracker"
PORT=8000

# Останавливаем старый сервис (если есть)
systemctl stop roulette.service 2>/dev/null || true

# Обновляем пакеты и ставим Python + git
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

# Клонируем репозиторий заново
rm -rf "$APP_DIR"
git clone "$REPO" "$APP_DIR"

cd "$APP_DIR"

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Создаём systemd-сервис
cat >/etc/systemd/system/roulette.service <<EOF
[Unit]
Description=Roulette Tracker Prediction Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn server:app --host 0.0.0.0 --port $PORT
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Запускаем сервис
systemctl daemon-reload
systemctl enable roulette.service
systemctl restart roulette.service

sleep 3
systemctl status roulette.service --no-pager || true

IP=\$(hostname -I | awk '{print \$1}')
echo "Roulette server running at: http://\$IP:$PORT/"
