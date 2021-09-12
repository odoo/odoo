import logging
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

_logger = logging.getLogger(__name__)


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
    def __init__(self, database_name):
        self.conn = psycopg2.connect(
            host=config.get("db_host"),
            database=database_name,
            user=config.get("db_user"),
            password=config.get("db_password"))

    def handle_vendors(self):
        "id, country_id, name, marketplace_id"
        count = get_all_dist_count(1, 0)
        insert_into_marketplace_dists = """INSERT INTO aumet_marketplace_distributor
                                    (name, country_id, id,
                                     create_uid, create_date, write_uid, write_date) 
                                    VALUES(%s, %s, %s, %s, %s, %s, %s);
                                    """
        update_marketplace_dists = """UPDATE aumet_marketplace_distributor
                                    SET "name"=%s, country_id=%s, write_uid=2,
                                      write_date=%s WHERE id=%s;"""

        for j in range(0, count, 1000):
            distributors = get_all_dist(1000, j)["data"]["data"]
            cur = self.conn.cursor()

            for i in distributors:
                try:
                    cur.execute(insert_into_marketplace_dists, (i["name"], i["countryId"],
                                                                i["id"], 1, datetime.now(), 1, datetime.now()))
                except psycopg2.errors.UniqueViolation:
                    self.conn.rollback()
                    cur.execute(update_marketplace_dists, (i["name"], i["countryId"],
                                                           datetime.now(), i["id"]))

            self.conn.commit()

    def handle_payment_methods(self):
        payment_methods = [(1, "Cheque on delivery"),
                           (2, "Cash on delivery"),
                           (3, "Cash Collection"),
                           (4, "Cheque Collection"),
                           (5, "Payment by Credit Facility"),
                           (6, "Managed by Seller")]

        insert_payment_query = """INSERT INTO aumet_payment_method (marketplace_payment_method_id, 
                                    name, create_uid, create_date, write_uid, write_date) 
                                    VALUES (%s,%s,%s,%s,%s,%s)"""

        update_query = """UPDATE public.aumet_payment_method
                        SET "name"=%s, write_date=%s
                        WHERE marketplace_payment_method_id=%s;"""

        cur = self.conn.cursor()
        for i in range(len(payment_methods)):
            try:
                cur.execute(insert_payment_query, (payment_methods[i][0], payment_methods[i][1],  1, datetime.now(), 1, datetime.now()))
            except psycopg2.errors.UniqueViolation:
                self.conn.rollback()
                cur.execute(update_query, (payment_methods[i][1], datetime.now(),payment_methods[i][0]))
            self.conn.commit()

    def handle_products(self):
        count = get_items_count()

        update_statement = """UPDATE public.aumet_marketplace_product
                                SET "name"=%s, unit_price=%s, marketplace_distributor=%s,
                                is_archived=%s, is_locked=%s, create_uid=1, write_date=%s
                                WHERE id=%s;"""

        insert_into_marketplace_products = """INSERT INTO aumet_marketplace_product
                                (name, unit_price, marketplace_distributor, is_archived, is_locked,
                                 id, create_uid, create_date, write_uid, write_date) 
                                VALUES(%s,%s,%s, %s, %s, %s, %s, %s, %s, %s);
                                """

        for j in range(0, count, 1000):
            products = get_all_product_details(1000, j)["data"]["data"]
            cur = self.conn.cursor()

            for i in products:
                try:
                    cur.execute(insert_into_marketplace_products, (i["productName_en"], i["unitPrice"],
                                                                   i["entityId"],
                                                                   bool(i["isArchived"]), bool(i["is_product_locked"]),
                                                                   i['id'],
                                                                   1, datetime.now(), 1, datetime.now()))
                    self.conn.commit()
                except psycopg2.errors.UniqueViolation:
                    self.conn.rollback()
                    _logger.error("found a duplicate product, trying to update")
                    """UPDATE public.aumet_marketplace_product
                                                    SET "name"=%s, unit_price=%s, marketplace_distributor=%s,
                                                    is_archived=%s, is_locked=%s, write_date=%s
                                                    WHERE id=%s;"""
                    cur.execute(update_statement, (i["productName_en"], i["unitPrice"],
                                                   i["entityId"],
                                                   bool(i["isArchived"]), bool(i["is_product_locked"]),
                                                   datetime.now(), i['id']))
                    self.conn.commit()


if __name__ == "__main__":
    temp_connection = psycopg2.connect(
        host=config.get("db_host"),
        database="postgres",
        user=config.get("db_user"),
        password=config.get("db_password"))

    cursor = temp_connection.cursor()
    cursor.execute("""SELECT datname FROM pg_database WHERE datistemplate = false;""")
    databases = cursor.fetchall()

    for database in databases:
        _logger.info(f"WORKING ON DATABASE {database[0]}")
        target_db_connection = ProductSync(database[0])
        target_db_connection.handle_vendors()
        target_db_connection.handle_products()
        target_db_connection.handle_payment_methods()
