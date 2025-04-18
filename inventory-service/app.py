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

