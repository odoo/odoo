import json
import logging

import requests

from odoo.exceptions import ValidationError
from odoo.tools import config


def check_token(func):
    def func_wrapper(cls, token=None, *args, **kwargs):
        if token:
            return func(cls, token, *args, *kwargs)

        raise ValidationError("Please make sure your user has a marketplace assigned user from users settings")

    return func_wrapper


_logger = logging.getLogger(__name__)


class CartAPI:
    marketplace_host = config.get("marketplace_host")

    @classmethod
    @check_token
    def get_all_product_details(cls, token):
        url = f"{cls.marketplace_host}/v1/pharmacy/products?limit=1000"
        response = requests.post(url, headers={
            'Content-Type': 'application/json',
            'x-user-lang': 'en',
            'x-api-key': 'zTvkXwJSSRa5DVvTgQhaUW52DkpkeSz',
            'x-session-id': '123',
            'Cookie': 'PHPSESSID=adl0oj5l20ufa78t4ij2s7nl91',
            "x-access-token": token
        })

    @classmethod
    @check_token
    def get_product_details(cls, token, product_id):
        url = f"{cls.marketplace_host}/v1/pharmacy/products/{product_id}"

        payload = {}

        response = requests.request("GET", url, headers={
            'Content-Type': 'application/json',
            'x-user-lang': 'en',
            'x-api-key': 'zTvkXwJSSRa5DVvTgQhaUW52DkpkeSz',
            'x-session-id': '123',
            'Cookie': 'PHPSESSID=adl0oj5l20ufa78t4ij2s7nl91',
            "x-access-token": token
        }, data=payload)

        return response.json()

    @classmethod
    @check_token
    def add_item_to_cart(cls, token, buyer_id, product_marketplace_id, bonus_amount, amount, payment_method):
        url = f"{cls.marketplace_host}/v1/pharmacy/cart/product"
        payload = json.dumps({
            "entityProductId": product_marketplace_id,
            "quantity": amount+bonus_amount,
            "entityId": buyer_id,
            "paymentMethodId": payment_method
        })

        _logger.info("request outgoing to marketplace")
        _logger.info(payload)

        response = requests.post(url, headers={
            'Content-Type': 'application/json',
            'x-user-lang': 'en',
            'x-api-key': 'zTvkXwJSSRa5DVvTgQhaUW52DkpkeSz',
            'x-session-id': '123',
            'Cookie': 'PHPSESSID=adl0oj5l20ufa78t4ij2s7nl91',
            "x-access-token": token
        }, data=payload)

        return response

    @classmethod
    @check_token
    def get_disr_details(cls, token, dist_id):
        url = f"{cls.marketplace_host}/v1/distributor/{dist_id}/details"

        payload = {}

        response = requests.request("GET", url, headers={
                'Content-Type': 'application/json',
                'x-user-lang': 'en',
                'x-api-key': 'zTvkXwJSSRa5DVvTgQhaUW52DkpkeSz',
                'x-session-id': '123',
                'Cookie': 'PHPSESSID=adl0oj5l20ufa78t4ij2s7nl91',
                "x-access-token": token
            }, data=payload)

        return response.json()
