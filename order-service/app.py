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
