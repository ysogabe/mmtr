FROM python:3

WORKDIR /app

COPY requirements.txt .
RUN apt update \
    && apt install -y build-essential libglib2.0-dev bluez \
    && pip3 install bluepy azure-eventhub \
    && pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "src/mmtr.py"]
