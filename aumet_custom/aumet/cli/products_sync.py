from datetime import datetime

import psycopg2
from odoo.cli import Command

from odoo.tools import config
import requests

headers = {
    'Content-Type': 'application/json',
    'x-user-lang': 'en',
    'x-api-key': 'zTvkXwJSSRa5DVvTgQhaUW52DkpkeSz',
    'x-session-id': '123',
    'Cookie': 'PHPSESSID=adl0oj5l20ufa78t4ij2s7nl91',
    "x-access-token": config.get("marketplace_token")
}


def get_all_product_details(items_count, offset):
    url = f"{config.get('marketplace_host')}/v1/pharmacy/products?limit={items_count}&offset={offset}"
    return requests.get(url, headers=headers).json()


def get_all_dist(items_count, offset):
    url = f"{config.get('marketplace_host')}/v1/pharmacy/sellers?limit={items_count}&offset={offset}"
    return requests.get(url, headers=headers).json()


def get_items_count():
    return get_all_product_details(1, 0)["data"]["dataFilter"]["dataCount"]


def get_all_dist_count(items_count, offset):
    return get_all_dist(1, 0)["data"]["dataFilter"]["dataCount"]


class ProductSync(Command):
    conn = psycopg2.connect(
        host=config.get("db_host"),
        database="postgres",
        user=config.get("db_user"),
        password=config.get("db_password"))

    @classmethod
    def handle_vendors(cls):
        "id, country_id, name, marketplace_id"
        count = get_all_dist_count(1, 0)
        for i in range(0, count, 1000):
            distributors = get_all_dist(1000, i)["data"]["data"]
            cur = cls.conn.cursor()

            insert_into_marketplace_dists = """INSERT INTO aumet_marketplace_distributor
                            (name, country_id, marketplace_id,
                             create_uid, create_date, write_uid, write_date) 
                            VALUES(%s, %s, %s, %s, %s, %s, %s);
                            """

            for i in distributors:
                print(i)

                print(i["name"], i["countryId"],
                      i["id"],1, datetime.now(), 1, datetime.now())
                cur.execute(insert_into_marketplace_dists, (i["name"], i["countryId"],
                                                            i["id"], 1, datetime.now(), 1, datetime.now()))
            cls.conn.commit()



    @classmethod
    def handle_payment_methods(cls):
        payment_methods = [(1, "Cheque on delivery"),
                           (2, "Cash on delivery"),
                           (3, "Cash Collection"),
                           (4, "Cheque Collection"),
                           (5, "Payment by Credit Facility"),
                           (6, "Managed by Seller")]

        insert_payment_query = """INSERT INTO aumet_payment_method (marketplace_payment_method_id, 
                                    name, create_uid, create_date, write_uid, write_date) VALUES """

        cur = cls.conn.cursor()
        for i in range(len(payment_methods)):
            val = f"""({payment_methods[i][0]}, '{payment_methods[i][1]}', 1, '{datetime.now()}', 1, '{datetime.now()}')"""
            insert_payment_query += (val + ",") if i != len(payment_methods) - 1 else val

        cur.execute(insert_payment_query)
        cls.conn.commit()

    @classmethod
    def handle_products(cls):
        count = get_items_count()
        for i in range(0, count, 1000):
            products = get_all_product_details(1000, i)["data"]["data"]
            cur = cls.conn.cursor()

            insert_into_marketplace_products = """INSERT INTO aumet_marketplace_product
                        (name, unit_price, marketplace_seller_id, is_archived, is_locked,
                         marketplace_id, create_uid, create_date, write_uid, write_date) 
                        VALUES(%s,%s,%s, %s, %s, %s, %s, %s, %s, %s);
                        """

            for i in products:
                cur.execute(insert_into_marketplace_products, (i["productName_en"], i["unitPrice"],
                                                               i["entityId"],
                                                               bool(i["isArchived"]), bool(i["is_product_locked"]),
                                                               i['id'],
                                                               1, datetime.now(), 1, datetime.now()))
                cls.conn.commit()


if __name__ == "__main__":
    # ProductSync.handle_products()
    # ProductSync.handle_payment_methods()
    ProductSync.handle_vendors()
