#!/bin/bash
set -euo pipefail

# Simple installer for Roulette Tracker Server
# IMPORTANT: if you run this from a cloned GitHub repo, REPO is not used.
REPO="https://github.com/Nikoo4/deed"
APP_DIR="/opt/roulette-tracker"
PORT="8000"

# Stop existing service if present
systemctl stop roulette.service 2>/dev/null || true

# Update packages
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git

# Prepare application directory
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"

# If running from remote (curl | bash), clone repo; otherwise copy current directory
if [[ "${RUN_FROM_REPO:-0}" == "1" ]]; then
    git clone "$REPO" "$APP_DIR"
else
    # Assume script is executed from inside project root that contains server.py, requirements.txt, roulette.service
    cp server.py requirements.txt roulette.service "$APP_DIR"/
fi

cd "$APP_DIR"

# Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install systemd service
cp roulette.service /etc/systemd/system/roulette.service

systemctl daemon-reload
systemctl enable roulette.service
systemctl restart roulette.service

sleep 3
systemctl status roulette.service --no-pager || true

IP=$(hostname -I | awk '{print $1}')
echo "Roulette Tracker server running at: http://$IP:$PORT/"
