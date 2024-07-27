#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock
from app import (
    StructureValidator, NameTransformer, PriceTransformer, 
    CurrencyTransformer, OrderProcessor
)

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
        self.assertFalse(self.validator.validate(invalid_order))

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
        result = self.transformer.transform(order)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Name contains non-English characters.")

    def test_non_capitalized_name(self):
        ''' 非大寫字母開頭的名字 '''
        order = {"name": "invalid name"}
        result = self.transformer.transform(order)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Name is not capitalized.")

class TestPriceTransformer(unittest.TestCase):
    def setUp(self):
        self.transformer = PriceTransformer()

    def test_valid_price(self):
        ''' 合法的價格 '''
        order = {"price": "1000"}
        result = self.transformer.transform(order)
        self.assertEqual(result, order)

    def test_price_over_2000(self):
        ''' 價格超過 2000 '''
        order = {"price": "2001"}
        result = self.transformer.transform(order)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Price is over 2000.")

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
        self.assertEqual(result["price"], "3100")

    def test_invalid_currency(self):
        ''' 錯誤的幣別 '''
        order = {"currency": "EUR", "price": "100"}
        result = self.transformer.transform(order)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Currency format is wrong.")

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
        self.validator.validate.return_value = False

        result, status_code = self.processor.process(order_data)
        self.assertEqual(status_code, 400)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Invalid JSON received")

    def test_transformation_error(self):
        ''' 轉換過程中發生錯誤 '''
        order_data = {"test": "data"}
        self.validator.validate.return_value = True
        self.transformers[0].transform.return_value = {"error": "Test error", "message": "Test message"}

        result, status_code = self.processor.process(order_data)
        self.assertEqual(status_code, 400)
        self.assertIn("error", result)
        self.assertEqual(result["message"], "Test message")

if __name__ == '__main__':
    unittest.main()