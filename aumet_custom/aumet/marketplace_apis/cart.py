import json
import requests

class CartAPI:

    @classmethod
    def get_product_details(cls,product_id, token):
        url = f"https://dev-mpapi.aumet.tech/v1/pharmacy/products/{product_id}"

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
    def add_item_to_cart(cls, token, buyer_id, product_marketplace_id, bonus_amount, amount, payment_method):
        url = "https://dev-mpapi.aumet.tech/v1/pharmacy/cart/product"
        payload = json.dumps({
            "entityProductId": product_marketplace_id,
            "quantity": amount+bonus_amount,
            "entityId": buyer_id,
            "paymentMethodId": payment_method
        })

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
    def get_disr_details(cls,token,dist_id):
        url = f"https://dev-mpapi.aumet.tech/v1/distributor/{dist_id}/details"

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
