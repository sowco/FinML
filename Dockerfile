# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные пакеты
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем TA-Lib (если используешь .deb)
COPY ta-lib_0.6.4_amd64.deb .
RUN dpkg -i ta-lib_0.6.4_amd64.deb || apt-get install -f -y

# Обновляем pip
RUN pip install --upgrade pip

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта
COPY . .

# Запуск приложения
CMD ["python", "main.py"]

#Строка для монтирования директории при старте
#docker run --rm -it -v "/home/***/bybit_prod:/app" bybit_app
