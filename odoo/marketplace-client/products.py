import json
import os
from pprint import pprint

import requests

# from .data import generate_pharmacy_order_request


class MarketAPIClient:
    HOST = os.environ["MARKET_PLACE_API_HOST"]
    headers = {
        "content-type": "application/json",
        "Accept": "application/json",
        "x-user-lang": "en",
        "x-api-key": "zTvkXwJSSRa5DVvTgQhaUW52DkpkeSz",
        "x-device-os": "python",
        "x-session-id": "",
        "x-access-token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOjI2MSwidXNlckVtYWlsIjoiYS50YXllaCtwaGFybWEyQGF1bWV0LmNvbSIsImZ1bGxOYW1lIjoiQWJlZCBQaGFybWFjeSIsImV4cCI6MjI1ODA5NzY2NX0.47gsGfEllC5PyFCu6NCiyseW-ZTzSGF3CCy5aAa7sjg"
    }

    @classmethod
    def get_all_products_by_dist(cls, dist_id):
        return json.loads(requests.get(f"{cls.HOST}/v1/distributor/{dist_id}", headers=cls.headers).content)

    @classmethod
    def get_all_featured_products_by_dist(cls, dist_id):
        print(requests.get(f"{cls.HOST}/v1/distributor/{dist_id}/featured", headers=cls.headers).content)
        return json.loads(requests.get(f"{cls.HOST}/v1/distributor/{dist_id}/featured", headers=cls.headers).content)

    @classmethod
    def get_all_distributors(cls):
        print(f"{cls.HOST}/v1/pharmacy/distributor")
        return json.loads(
            requests.get(f"{cls.HOST}/v1/pharmacy/distributor", headers=cls.headers).content)
    #
    @classmethod
    def create_pharmacy_order(cls, pharmacy_id, distributor_id, payment_method, notes):
        return requests.post(f"{cls.HOST}/v1/pharmacy/orders",
                             data=generate_pharmacy_order_request(pharmacy_id, distributor_id, payment_method, notes),
                             headers=cls.headers
                             ).content

    @classmethod
    def get_orders_list(cls):
        return requests.get(f"{cls.HOST}/v1/pharmacy/orders", headers=cls.headers).content

if __name__ == "__main__":
    pprint(MarketAPIClient.get_all_distributors())
    pprint(MarketAPIClient.get_all_featured_products_by_dist(193))
    pprint(MarketAPIClient.get_all_products_by_dist(1))