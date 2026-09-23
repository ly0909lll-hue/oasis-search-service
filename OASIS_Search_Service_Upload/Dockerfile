FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY gateway.py /app/gateway.py
EXPOSE 8080
CMD ["python", "/app/gateway.py"]
