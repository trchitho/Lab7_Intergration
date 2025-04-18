Hướng dẫn Triển khai Chi tiết Lab 7:  Integration Style - Remote Procedure Invocation (HTTP Synchronous)
Mục tiêu:
•	Hiểu Remote Procedure Invocation (RPI/RPC): Trải nghiệm cách một ứng dụng (order-service) gọi trực tiếp một hàm/thủ tục (thông qua API endpoint) của một ứng dụng khác (inventory-service) để thực hiện một tác vụ và nhận kết quả trả về 
•	Nhận biết phụ thuộc chặt chẻ (Tight Coupling): Thấy rõ sự phụ thuộc lẫn nhau giữa hai service khi giao tiếp đồng bộ. Nếu service được gọi bị lỗi hoặc chậm, service gọi sẽ bị ảnh hưởng trực tiếp 
•	Thực hành Xử lý Lỗi Đồng bộ: Lập trình cách xử lý các tình huống lỗi phổ biến khi gọi API đồng bộ như timeout (hết thời gian chờ), service không khả dụng, hoặc các lỗi logic nghiệp vụ (hết hàng, không tìm thấy sản phẩm) 
Chuẩn bị:
•	Docker và Docker Compose: Đã cài đặt trên máy tính.
•	Trình soạn thảo code: Bất kỳ trình soạn thảo nào (VS Code, Sublime Text, Notepad++).
•	Python 3
•	Thư viện Python: Flask (để tạo web service), Requests (để thực hiện HTTP client call)
Chuẩn bị:
•	Để xác nhận đơn hàng, order-service phải gọi đồng bộ (synchronous request/response) đến một endpoint của inventory-service để kiểm tra xem mặt hàng yêu cầu có đủ số lượng tồn kho hay không 
•	inventory-service cung cấp một API (/check-stock/<product_id>) để thực hiện việc kiểm tra này và trả về số lượng tồn kho hiện tại hoặc lỗi 
•	Dựa trên kết quả trả về từ inventory-service, order-service sẽ quyết định xác nhận (confirm) hay từ chối (reject) đơn hàng.
Cấu trúc thư mục
•	Lab7_/
o	order-service/
	app.py	# Code Flask cho Order Service
	Dockerfile	# Định nghĩa build image cho OrderService
o	inventory-service/
	app.py	# Code Flask cho Inventory Service
	Dockerfile	# Định nghĩa build image cho Inventory Service
o	docker-compose.yml # File điều phối chạy các service
 
Bước 1.	Viết code inventory-service (app.py): 
Python
from flask import Flask, jsonify, request
import time
import random

app = Flask(__name__)

# Dữ liệu tồn kho giả lập
INVENTORY = {"product_123": 10, "product_456": 0, "product_789": 5}

@app.route('/check-stock/<product_id>', methods=['GET'])
def check_stock(product_id):
    print(f"Received stock check request for {product_id}")

    # Giả lập thời gian xử lý
    processing_time = random.uniform(0.1, 1.0) # Thời gian ngẫu nhiên từ 0.1s đến 1s
    print(f"Processing time: {processing_time:.2f}s")
    time.sleep(processing_time)

    # Giả lập lỗi không tìm thấy sản phẩm
    if product_id not in INVENTORY:
        print(f"Product {product_id} not found.")
        return jsonify({"error": "Product not found"}), 404

    stock = INVENTORY.get(product_id, 0)
    print(f"Stock for {product_id}: {stock}")
    return jsonify({"product_id": product_id, "stock": stock}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)

Bước 2.	Tạo Dockerfile cho inventory-service: 
Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY app.py .
RUN pip install --no-cache-dir Flask
EXPOSE 5002
CMD ["python", "app.py"]
Bước 3.	Viết code order-service (app.py): 
Python
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

INVENTORY_SERVICE_URL = os.environ.get('INVENTORY_SERVICE_URL', 'http://inventory-service:5002')
ORDERS = [] # Lưu đơn hàng đơn giản trong bộ nhớ

@app.route('/create-order', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data or 'product_id' not in data or 'quantity' not in data:
        return jsonify({"error": "Missing product_id or quantity"}), 400

    product_id = data['product_id']
    quantity_needed = data['quantity']

    print(f"Received order for {quantity_needed} of {product_id}. Checking inventory...")

    # === Lời gọi RPC (HTTP Synchronous) ===
    try:
        inventory_url = f"{INVENTORY_SERVICE_URL}/check-stock/{product_id}"
        print(f"Calling Inventory Service: {inventory_url}")
        # Đặt timeout để tránh chờ đợi quá lâu
        response = requests.get(inventory_url, timeout=2.0) # Timeout sau 2 giây

        response.raise_for_status() # Ném exception nếu status code là 4xx hoặc 5xx

        inventory_data = response.json()
        stock = inventory_data.get('stock', 0)

        print(f"Inventory check successful. Stock: {stock}")

        if stock >= quantity_needed:
            # Logic tạo đơn hàng (giả lập)
            order_id = len(ORDERS) + 1
            order = {"id": order_id, "product_id": product_id, "quantity": quantity_needed, "status": "confirmed"}
            ORDERS.append(order)
            print(f"Order {order_id} confirmed.")
            return jsonify({"status": "Order confirmed", "order": order}), 200
        else:
            print(f"Insufficient stock for {product_id}. Needed: {quantity_needed}, Available: {stock}")
            return jsonify({"status": "Order rejected", "reason": "Insufficient stock"}), 400 # 400 Bad Request có thể hợp lý hơn

    except requests.exceptions.Timeout:
        print("Inventory service timed out.")
        return jsonify({"error": "Inventory service timed out"}), 504 # 504 Gateway Timeout
    except requests.exceptions.RequestException as e:
        print(f"Error calling inventory service: {e}")
        # Check nếu là lỗi 404 từ inventory service
        if e.response is not None and e.response.status_code == 404:
             return jsonify({"status": "Order rejected", "reason": "Product not found in inventory"}), 400
        return jsonify({"error": f"Inventory service unavailable: {e}"}), 503 # 503 Service Unavailable
    # =====================================

@app.route('/orders', methods=['GET'])
def get_orders():
    return jsonify(ORDERS), 200


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
Bước 4.	Tạo Dockerfile cho order-service: 
Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY app.py .
RUN pip install --no-cache-dir Flask requests
EXPOSE 5000
ENV INVENTORY_SERVICE_URL=http://inventory-service:5002
CMD ["python", "app.py"]
Bước 5.	Tạo docker-compose.yml: 
YAML
version: '3.8'

services:
  order_service_b: # Đổi tên để tránh xung đột nếu chạy cùng lab khác
    build: ./order-service
    container_name: order_service_b
    ports:
      - "5000:5000" # Giữ port 5000
    environment:
      - INVENTORY_SERVICE_URL=http://inventory_service_b:5002
    networks:
      - labB-net
    depends_on:
      - inventory_service_b

  inventory_service_b:
    build: ./inventory-service
    container_name: inventory_service_b
    # Port 5002 không cần mở ra ngoài
    networks:
      - labB-net

networks:
  labB-net:
    driver: bridge
Bước 6.	Chạy hệ thống: 
Bash
docker-compose up --build -d
Bước 7.	Kiểm thử: 
o	Dùng Postman/curl gửi POST request đến http://localhost:5000/create-order với body: 
	{"product_id": "product_123", "quantity": 10} -> Mong đợi thành công (200 OK).
 
 
	{"product_id": "product_123", "quantity": 15} -> Mong đợi lỗi không đủ hàng (400 Bad Request).
 
	{"product_id": "product_unknown", "quantity": 1} -> Mong đợi lỗi không tìm thấy sản phẩm (400 Bad Request).
 
o	Kiểm tra độ trễ/lỗi: 
	Chỉnh time.sleep() trong inventory-service lên cao (ví dụ 3 giây) và chạy lại docker-compose up --build -d inventory_service_b. Gửi lại request tạo đơn hàng -> Mong đợi lỗi timeout (504 Gateway Timeout) từ order-service.
 
	Dừng inventory-service: docker-compose stop inventory_service_b. Gửi lại request tạo đơn hàng -> Mong đợi lỗi service unavailable (503 Service Unavailable).
 
Bước 8.	Dọn dẹp: 
Bash
docker-compose down

Kết quả mong đợi Lab 7:
•	Sinh viên chạy được 2 service.
•	order-service gọi thành công API của inventory-service để kiểm tra tồn kho khi tạo đơn hàng.
•	Khi inventory-service phản hồi chậm hoặc bị dừng, order-service trả về lỗi timeout hoặc unavailable tương ứng, cho thấy sự phụ thuộc chặt chẽ và ảnh hưởng của lời gọi đồng bộ.
•	Sinh viên hiểu được cách xử lý các lỗi phổ biến (timeout, connection error, 4xx/5xx) khi thực hiện lời gọi RPC/HTTP đồng bộ.
