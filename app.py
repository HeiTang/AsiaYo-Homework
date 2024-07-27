#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from abc import ABC, abstractmethod
from flask import Flask, request, jsonify

class OrderValidator(ABC):
    @abstractmethod
    def validate(self, order_data):
        pass

class StructureValidator(OrderValidator):

    expected_structure = {
        "id": str,
        "name": str,
        "address": {
            "city": str,
            "district": str,
            "street": str
        },
        "price": str,
        "currency": str
    }

    def validate(self, order_data, expected = expected_structure):
        # 檢查 order_data 是否為 dict
        if not isinstance(order_data, dict):
            return False

        # 遞迴檢查 order_data 是否符合預期的資料結構與型態
        for key, value_type in expected.items():
            # 檢查 key 是否存在
            if key not in order_data:
                return False

            # 若 value 的 為型態為 dict，則遞迴檢查
            if isinstance(value_type, dict):
                if not self.validate(order_data[key], value_type):
                    return False

            # 檢查 order_data 的 value 是否為指定型態
            elif not isinstance(order_data[key], value_type):
                return False
        return True

class OrderTransformer(ABC):
    @abstractmethod
    def transform(self, order_data):
        pass

class NameTransformer(OrderTransformer):
    def transform(self, order_data):
        '''
        1. 訂單名稱若包含非英文字元(不含空格)，則回傳錯誤
        2. 訂單名稱若每個單字的字首字母非大寫，則回傳錯誤
        '''
        import unicodedata

        normalized_str = unicodedata.normalize('NFKD', order_data["name"])
        print(normalized_str)
        # normalized_str = normalized_str.encode('ascii', 'ignore').decode('utf-8')
        # print(normalized_str)
        if not re.match("^[A-Za-z ]+$", normalized_str):
            return {"error": "Bad Request", "message": "Name contains non-English characters."}

        if not order_data["name"].istitle():
            return {"error": "Bad Request", "message": "Name is not capitalized."}

        return order_data

class PriceTransformer(OrderTransformer):
    def transform(self, order_data):
        '''
        1. 若訂單價格超過 2000，則回傳錯誤
        '''
        if int(order_data["price"]) > 2000:
            return {"error": "Bad Request", "message": "Price is over 2000."}
        return order_data

class CurrencyTransformer(OrderTransformer):
    def transform(self, order_data):
        '''
        1. 若訂單幣別為 USD，則將價格轉換為 TWD 並更新幣別
        2. 若訂單幣別非 TWD 或 USD，則回傳錯誤
        '''
        order_currency = order_data["currency"]

        if order_currency not in ["TWD", "USD"]:
            return {"error": "Bad Request", "message": "Currency format is wrong."}
        
        if order_currency == "USD":
            order_data["price"] = str(int(order_data["price"]) * 31)
            order_data["currency"] = "TWD"
        return order_data

class OrderProcessor:
    def __init__(self, validator, transformers):
        self. validator = validator
        self.transformers = transformers

    def process(self, order_data):
        if not self.validator.validate(order_data):
            return {"error": "Bad Request", "message": "Invalid JSON received"}, 400
        
        for transformer in self.transformers:
            order_data = transformer.transform(order_data)
            if "error" in order_data:
                return order_data, 400
        
        return {"Success": "Order is processed.", "Order_data": order_data}, 200

app = Flask(__name__)

@app.route('/api/orders', methods=['POST'])
def process_order():
    request_data = request.get_json()
    processor = OrderProcessor(
        StructureValidator(),
        [NameTransformer(), PriceTransformer(), CurrencyTransformer()]
    )
    response, status_code = processor.process(request_data)
    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(port=5000)