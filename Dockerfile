# -------- Build stage --------
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# -------- Production stage --------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier les packages installés depuis le builder
COPY --from=builder /root/.local /root/.local
# Copier le code de l'application
COPY app/ .

# Définir le PATH et PYTHONPATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Exposer le port fourni par Dokploy
EXPOSE $PORT

# Copier et rendre executable l'entrypoint
COPY app/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Lancer le script entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD []
