#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import logging
import unicodedata
from abc import ABC, abstractmethod
from flask import Flask, request, jsonify

# 設定檔
import config as cfg

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrderProcessingError(Exception):
    def __init__(self, message, error_type="Bad Request"):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)

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
            raise OrderProcessingError("Invalid order data structure")

        # 遞迴檢查 order_data 是否符合預期的資料結構與型態
        for key, value_type in expected.items():
            # 檢查 key 是否存在
            if key not in order_data:
                raise OrderProcessingError(f"Missing key: {key}")

            # 若 value 的 為型態為 dict，則遞迴檢查
            if isinstance(value_type, dict):
                if not self.validate(order_data[key], value_type):
                    return False
            # 檢查 order_data 的 value 是否為指定型態
            elif not isinstance(order_data[key], value_type):
                raise OrderProcessingError(f"Invalid type for key {key}")
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
        normalized_str = unicodedata.normalize('NFKD', order_data["name"])

        if not re.match("^[A-Za-z ]+$", normalized_str):
            raise OrderProcessingError("Name contains non-English characters.")

        if not order_data["name"].istitle():
            raise OrderProcessingError("Name is not capitalized.")

        return order_data

class PriceTransformer(OrderTransformer):
    def transform(self, order_data):
        '''
        1. 若訂單價格超過 2000，則回傳錯誤
        2. 若訂單價格為負數，則回傳錯誤
        '''
        if int(order_data["price"]) > cfg.MAX_PRICE:
            raise OrderProcessingError(f"Price is over {cfg.MAX_PRICE}.")
        
        if int(order_data["price"]) < 0:
            raise OrderProcessingError("Price is negative.")
        return order_data

class CurrencyTransformer(OrderTransformer):
    def transform(self, order_data):
        '''
        1. 若訂單幣別為 USD，則將價格轉換為 TWD 並更新幣別
        2. 若訂單幣別非 TWD 或 USD，則回傳錯誤
        '''
        order_currency = order_data["currency"]

        if order_currency not in cfg.ALLOWED_CURRENCIES:
            raise OrderProcessingError("Currency format is wrong.")

        if order_currency == "USD":
            order_data["price"] = str(int(order_data["price"]) * cfg.USD_TO_TWD_RATE)
            order_data["currency"] = "TWD"
            logger.info(f"Converted price from USD to TWD: {order_data['price']}")
        return order_data

class OrderProcessor:
    def __init__(self, validator, transformers):
        self. validator = validator
        self.transformers = transformers

    def process(self, order_data):
        try:
            logger.info("Starting order processing")
            if not self.validator.validate(order_data):
                raise OrderProcessingError("Invalid JSON received")

            for transformer in self.transformers:
                order_data = transformer.transform(order_data)
                logger.info(f"Applied transformer: {transformer.__class__.__name__}")

            logger.info("Order processing completed successfully")
            return {"Success": "Order is processed.", "Order_data": order_data}, 200
        except OrderProcessingError as e:
            logger.error(f"Order processing failed: {str(e)}")
            return {"error": e.error_type, "message": str(e)}, 400

app = Flask(__name__)

@app.route('/api/orders', methods=['POST'])
def process_order():
    request_data = request.get_json()
    logger.info("Received new order request")
    processor = OrderProcessor(
        StructureValidator(),
        [NameTransformer(), PriceTransformer(), CurrencyTransformer()]
    )
    response, status_code = processor.process(request_data)
    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(port=5000)