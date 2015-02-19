# -*- coding: utf-8 -*-

from datetime import date
from openerp import fields
from openerp.tests.common import TransactionCase


class TestProductMargin(TransactionCase):

    def test_product_margin(self):
        ProductMargin = self.env['product.margin']
        Product = self.env['product.product']
        # I have to create margin detail
        product_margin = ProductMargin.create(dict(
            from_date=fields.Date.to_string(date(date.today().year, 1, 1)),
            to_date=fields.Date.to_string(date(date.today().year, 12, 31)),
            invoice_state='open_paid',
        ))

        context = {"lang": 'en_US',
                   "search_default_filter_to_sell": "1",
                   "active_model": "product.product",
                   "disable_log": True,
                   "tz": False,
                   "active_ids": [self.env.ref("product.product_product_5").id],
                   "active_id": self.env.ref("product.product_product_5").id}

        product_margin.with_context(context).action_open_window()

        product_field = ['sale_avg_price', 'expected_margin_rate',
                         'total_margin_rate', 'total_cost', 'sale_num_invoiced',
                         'total_margin', 'sales_gap', 'purchase_num_invoiced',
                         'expected_margin', 'turnover']

        product = Product.browse(product_margin.id)
        product.with_context(context).read(product_field)
