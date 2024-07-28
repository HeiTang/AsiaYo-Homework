#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, patch
from app import (
    StructureValidator, NameTransformer, PriceTransformer, 
    CurrencyTransformer, OrderProcessor, OrderProcessingError
)
import config as cfg

class TestStructureValidator(unittest.TestCase):
    def setUp(self):
        self.validator = StructureValidator()

    def test_valid_structure(self):
        ''' 合法的 JSON 結構 '''
        valid_order = {
            "id": "123",
            "name": "Test Order",
            "address": {
                "city": "Taipei",
                "district": "Xinyi",
                "street": "Main St"
            },
            "price": "1000",
            "currency": "TWD"
        }
        self.assertTrue(self.validator.validate(valid_order))

    def test_invalid_structure(self):
        ''' 非法的 JSON 結構 '''
        invalid_order = {
            "id": 123,  # Should be string
            "name": "Test Order",
            "address": {
                "city": "Taipei",
                "district": "Xinyi",
                # Missing street
            },
            "price": "1000",
            "currency": "TWD"
        }
        with self.assertRaises(OrderProcessingError):
            self.validator.validate(invalid_order)

class TestNameTransformer(unittest.TestCase):
    def setUp(self):
        self.transformer = NameTransformer()

    def test_valid_name(self):
        ''' 合法的名字 '''
        order = {"name": "Valid Name"}
        result = self.transformer.transform(order)
        self.assertEqual(result, order)

    def test_non_english_name(self):
        ''' 含有非英文字元的名字 '''
        order = {"name": "Invalid 名字"}
        with self.assertRaises(OrderProcessingError) as context:
            self.transformer.transform(order)
        self.assertEqual(str(context.exception), "Name contains non-English characters.")

    def test_non_capitalized_name(self):
        ''' 非大寫字母開頭的名字 '''
        order = {"name": "invalid name"}
        with self.assertRaises(OrderProcessingError) as context:
            self.transformer.transform(order)
        self.assertEqual(str(context.exception), "Name is not capitalized.")

class TestPriceTransformer(unittest.TestCase):
    def setUp(self):
        self.transformer = PriceTransformer()

    def test_valid_price(self):
        ''' 合法的價格 '''
        order = {"price": "1000", "currency": "TWD"}
        result = self.transformer.transform(order)
        self.assertEqual(result, order)

    def test_price_over_max(self):
        ''' 價格超過最大限制 '''
        order = {"price": str(cfg.MAX_PRICE + 1), "currency": "TWD"}
        with self.assertRaises(OrderProcessingError) as context:
            self.transformer.transform(order)
        self.assertEqual(str(context.exception), f"Price is over {cfg.MAX_PRICE}.")

    def test_negative_price(self):
        ''' 負數價格 '''
        order = {"price": "-100", "currency": "TWD"}
        with self.assertRaises(OrderProcessingError) as context:
            self.transformer.transform(order)
        self.assertEqual(str(context.exception), "Price is negative.")

    @patch('config.ALLOWED_CURRENCIES', {'TWD': 0, 'USD': 2})
    def test_price_decimal_places(self):
        ''' 測試不同貨幣的價格小數位數 '''
        test_cases = [
            # (幣別, 價格, 預期結果, 錯誤訊息)
            ("TWD", "1000", True, None),
            ("TWD", "1000.50", False, "Price has decimal places."),
            ("USD", "1000", True, None),
            ("USD", "1000.50", True, None),
            ("USD", "1000.555", False, "Price decimal places are wrong."),
        ]

        for currency, price, should_pass, error_message in test_cases:
            with self.subTest(currency=currency, price=price):
                order = {"price": price, "currency": currency}
                if should_pass:
                    result = self.transformer.transform(order)
                    self.assertEqual(result, order)
                else:
                    with self.assertRaises(OrderProcessingError) as context:
                        self.transformer.transform(order)
                    self.assertEqual(str(context.exception), error_message)

class TestCurrencyTransformer(unittest.TestCase):
    def setUp(self):
        self.transformer = CurrencyTransformer()

    def test_twd_currency(self):
        ''' TWD 幣別 '''
        order = {"currency": "TWD", "price": "1000"}
        result = self.transformer.transform(order)
        self.assertEqual(result, order)

    def test_usd_currency(self):
        ''' USD 幣別 '''
        order = {"currency": "USD", "price": "100"}
        result = self.transformer.transform(order)
        self.assertEqual(result["currency"], "TWD")
        self.assertEqual(result["price"], str(int(100 * cfg.USD_TO_TWD_RATE)))

    def test_invalid_currency(self):
        ''' 錯誤的幣別 '''
        order = {"currency": "EUR", "price": "100"}
        with self.assertRaises(OrderProcessingError) as context:
            self.transformer.transform(order)
        self.assertEqual(str(context.exception), "Currency format is wrong.")

class TestOrderProcessor(unittest.TestCase):
    def setUp(self):
        self.validator = Mock()
        self.transformers = [Mock(), Mock(), Mock()]
        self.processor = OrderProcessor(self.validator, self.transformers)

    def test_valid_order(self):
        ''' 合法的訂單 '''
        order_data = {"test": "data"}
        self.validator.validate.return_value = True
        for transformer in self.transformers:
            transformer.transform.return_value = order_data

        result, status_code = self.processor.process(order_data)
        self.assertEqual(status_code, 200)
        self.assertIn("Success", result)

    def test_invalid_structure(self):
        ''' 非法的 JSON 結構 '''
        order_data = {"test": "data"}
        self.validator.validate.side_effect = OrderProcessingError("Invalid JSON received")

        result, status_code = self.processor.process(order_data)
        self.assertEqual(status_code, 400)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Invalid JSON received")

    def test_transformation_error(self):
        ''' 轉換過程中發生錯誤 '''
        order_data = {"test": "data"}
        self.validator.validate.return_value = True
        self.transformers[0].transform.side_effect = OrderProcessingError("Test error")

        result, status_code = self.processor.process(order_data)
        self.assertEqual(status_code, 400)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Test error")

if __name__ == '__main__':
    unittest.main()