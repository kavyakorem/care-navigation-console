FROM node:22-alpine AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py app.py ./
COPY --from=web /web/dist ./web/dist
RUN useradd --create-home runner
USER runner
ENV PORT=8080
EXPOSE 8080
CMD ["python", "app.py"]
