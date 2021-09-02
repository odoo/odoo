from datetime import datetime
from math import ceil
from pprint import pprint

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
    print(headers)
    return requests.get(url, headers=headers).json()


def get_items_count():
    print(get_all_product_details(1, 0))
    return get_all_product_details(1, 0)["data"]["dataFilter"]["dataCount"]


class DatabaseOps:
    @classmethod
    def retrieve_payment_methods(cls):
        cursor = cls.mydb.cursor()

        cursor.execute("select id, name_en, name_ar,name_fr from paymentMethod")
        columns = ["id", "name_en", "name_ar", "name_fr"]

        return [dict(zip(columns, i)) for i in cursor.fetchall()]

    @classmethod
    def retrieve_vendors(cls):
        cursor = cls.mydb.cursor()

        cursor.execute("""select e.id ,e.name_en as name, country.name_en as country ,
                            currency.shortName as currency from entity e
                            inner join  country  on e.countryId = country.id
                    inner join  currency   on e.currencyId = currency.id""")

        columns = ["marketplace_id", "name", "country", "currency"]

        vendors = []
        for i in cursor.fetchall():
            vendors.append(dict(zip(columns, i)))
        return vendors


class ProductSync(Command):
    conn = psycopg2.connect(
        host=config.get("db_host"),
        database="postgres",
        user=config.get("db_user"),
        password=config.get("db_password"))

    def handle_vendors(self):
        vendors = DatabaseOps.retrieve_vendors()

        countries = set()
        [countries.add(vendor["country"]) for vendor in vendors]

        cur = self.conn.cursor()

        country_mapping = {}

        for i in countries:
            query = f"select id from public.res_country where name ilike '{i}'"
            cur.execute(query)
            country_mapping[i] = cur.fetchone()

        insert_vendor = """INSERT INTO public.res_partner
                                    ("name", create_date,  active, country_id, company_name, display_name, create_uid,
                                     write_uid, write_date, marketplace_id)
                                    VALUES( %s, %s, true, %s, %s, %s, 1, 1, %s, %s);
                                """

        for i in vendors:
            cur.execute(insert_vendor, (i["name"], datetime.now(), country_mapping[i["country"]],
                                        i["name"], i["name"], datetime.now(), i["marketplace_id"]))
            self.conn.commit()

    @classmethod
    def handle_payment_methods(cls):
        payment_methods = DatabaseOps.retrieve_payment_methods()
        insert_payment_query = """INSERT INTO public.aumet_payment_method (marketplace_payment_method_id, 
                                name, create_uid, create_date, write_uid, write_date) VALUES """

        cur = cls.conn.cursor()
        for i in range(len(payment_methods)):
            val = f"""({payment_methods[i]["id"]}, '{payment_methods[i]["name_en"]}', 1, '{datetime.now()}', 1, '{datetime.now()}')"""
            insert_payment_query += (val + ",") if i != len(payment_methods) - 1 else val

        cur.execute(insert_payment_query)
        cls.conn.commit()

    @classmethod
    def handle_products(cls):
        count = get_items_count()
        for i in range(0, count, 1000):
            products = get_all_product_details(1000, i)["data"]["data"]
            cur = cls.conn.cursor()

            insert_into_marketplace_products = """INSERT INTO public.aumet_marketplace_product
                    (name, unit_price, marketplace_seller_id, is_archived, is_locked,
                     marketplace_id, create_uid, create_date, write_uid, write_date) 
                    VALUES(%s,%s,%s, %s, %s, %s, %s, %s, %s, %s);
                    """

            for i in products:
                cur.execute(insert_into_marketplace_products, (i["entityName_en"], i["unitPrice"],
                                                               i['id'],
                                                               bool(i["isArchived"]), bool(i["is_product_locked"]),
                                                               i["entityId"],
                                                               1, datetime.now(), 1, datetime.now()))
                cls.conn.commit()


if __name__ == "__main__":
    print(config.get("marketplace_token", ""))
    print(headers)
    ProductSync.handle_products()
    # print(ProductSync.handle_payment_methods())
