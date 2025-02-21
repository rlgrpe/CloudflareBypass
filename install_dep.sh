#!/bin/bash

set -e

# Обновление пакетов
sudo apt update && sudo apt upgrade -y

# Установка Google Chrome
if ! command -v google-chrome &> /dev/null; then
    wget -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo apt install -y /tmp/google-chrome.deb
    rm /tmp/google-chrome.deb
else
    echo "Google Chrome already exist."
fi

# Установка зависимостей для Python
sudo apt install -y software-properties-common

# Добавление репозитория deadsnakes для Python 3.11
if ! grep -q "deadsnakes" /etc/apt/sources.list /etc/apt/sources.list.d/*; then
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
fi

# Установка Python 3.11.5
sudo apt install -y python3.11 python3.11-dev python3.11-tk python3.11-venv

# Установка pip для Python 3.11
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.11

# Проверка установки Python и pip
python3.11 --version
pip --version

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
    echo "Venv created"
else
    echo "Venv exist"
fi

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей из requirements.txt
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "Deps installed"
else
    echo "File requirements.txt not found. Skip install deps."
fi

# Открытие порта 8000
sudo ufw allow 8000/tcp
sudo systemctl restart ufw

echo "Port 8000 open!"