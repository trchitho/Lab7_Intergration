FROM python:3.9-slim
WORKDIR /app
COPY app.py .
RUN pip install --no-cache-dir Flask requests
EXPOSE 5000
ENV INVENTORY_SERVICE_URL=http://inventory-service:5002
CMD ["python", "app.py"]
