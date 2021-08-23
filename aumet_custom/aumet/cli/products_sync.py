from datetime import datetime

import psycopg2

from odoo.cli import Command
import mysql.connector
from odoo.tools import config


class DatabaseOps:
    mydb = mysql.connector.connect(
        host="aumet-mysql-dev.cdl2a0vfb1as.me-south-1.rds.amazonaws.com",
        user="root",
        database="marketplace",
        password="eG>W&K`mD7r;r>wR"
    )

    @classmethod
    def retrieve_payment_methods(cls):
        cursor = cls.mydb.cursor()

        cursor.execute("select id, name_en, name_ar,name_fr from paymentMethod")
        columns = ["id", "name_en", "name_ar", "name_fr"]

        return [dict(zip(columns, i)) for i in cursor.fetchall()]

    @classmethod
    def retrieve_products(cls):
        cursor = cls.mydb.cursor()

        cursor.execute(
            """
            select
            p.id,
            p.scientificNameId,
            p.madeInCountryId,
            p.details,
            p.insertDateTime,
            p.name_en,
            p.name_ar,
            p.name_fr,
            p.subtitle_en,
            p.subtitle_ar,
            p.subtitle_fr,
            p.description_en,
            p.description_ar,
            p.description_fr,
            p.strength,
            p.manufacturerName,
            p.batchNumber,
            p.itemCode,
            p.expiryDate,
            p.categoryId,
            p.subcategoryId,
            p.image,
            p.imageAlt,
            p.barcode,
            eps.unitPrice,
            eps.isArchived,
            eps.is_locked,
            eps.id as marketplace_sell_id,
            eps.entityId as marketplace_seller_reference
             from product as p inner join entityProductSell eps on p.id=eps.productId
            """
        )
        columns = [
            "id", "scientificNameId", "madeInCountryId", "details", "insertDateTime", "name_en", "name_ar",
            "name_fr", "subtitle_en", "subtitle_ar", "subtitle_fr", "description_en", "description_ar",
            "description_fr", "strength", "manufacturerName", "batchNumber", "itemCode", "expiryDate",
            "categoryId", "subcategoryId", "image", "imageAlt", "barcode", "unitPrice", "isArchived",
            "is_locked", "marketplace_sell_id", "marketplace_seller_reference"
        ]
        products = []
        for i in cursor.fetchall():
            products.append(dict(zip(columns, i)))
        return products



class product_sync(Command):
    def run(self, args):
        conn = psycopg2.connect(
            host=config.get("db_host"),
            database="postgres",
            user=config.get("db_user"),
            password=config.get("db_password"))

        cur = conn.cursor()

        payment_methods = DatabaseOps.retrieve_payment_methods()
        insert_payment_query = """INSERT INTO public.aumet_payment_method (marketplace_payment_method_id, 
                        name, create_uid, create_date, write_uid, write_date) VALUES """
        for i in range(len(payment_methods)):
            val = f"""({payment_methods[i]["id"]}, '{payment_methods[i]["name_en"]}', 1, '{datetime.now()}', 1, '{datetime.now()}')"""
            insert_payment_query += (val + ",") if i != len(payment_methods) - 1 else val
        cur.execute(insert_payment_query)
        products = DatabaseOps.retrieve_products()

        insert_into_marketplace_products = """INSERT INTO public.aumet_marketplace_product
                (name, unit_price, marketplace_seller_id, is_archived, is_locked,
                 marketplace_id, create_uid, create_date, write_uid, write_date) 
                VALUES(%s,%s,%s, %s, %s, %s, %s, %s, %s, %s);
                """
        for i in products:
            cur.execute(insert_into_marketplace_products, (i["name_en"], i["unitPrice"],
                                                           i['marketplace_seller_reference'],
                                                           bool(i["isArchived"]), bool(i["is_locked"]),
                                                           i["marketplace_sell_id"],
                                                           1, datetime.now(), 1, datetime.now()))
            conn.commit()

