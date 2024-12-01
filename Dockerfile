FROM python:3.9-slim

WORKDIR /app

# Installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice del server
COPY server.py .

# Esponi la porta OPC UA
EXPOSE 4840

# Avvia il server
CMD ["python", "server.py"]