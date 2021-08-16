import requests
import json


class CartAPI:

    @classmethod
    def add_item_to_cart(cls, token, buyer_id, product_marketplace_id, bonus_amount, amount, payment_method):
        url = "https://dev-mpapi.aumet.tech/v1/pharmacy/cart/product"
        payload = json.dumps({
            "entityProductId": product_marketplace_id,
            "quantity": amount+bonus_amount,
            "entityId": buyer_id,
            "paymentMethodId": payment_method
        })
        print("PAYLOAD ")
        print(payload)

        response = requests.post(url, headers={
            'Content-Type': 'application/json',
            'x-user-lang': 'en',
            'x-api-key': 'zTvkXwJSSRa5DVvTgQhaUW52DkpkeSz',
            'x-session-id': '123',
            'Cookie': 'PHPSESSID=adl0oj5l20ufa78t4ij2s7nl91',
            "x-access-token": token
        }, data=payload)
        print(response.json())
        return response
