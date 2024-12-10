# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests import HttpCase, tagged


class TestProductGMCCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.color_attribute = cls.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [
                Command.create({ 'name': 'white', 'sequence': 1 }),
                Command.create({ 'name': 'black', 'sequence': 2, 'default_extra_price': 20.0 }),
            ],
        })
        (
            cls.color_attribute_white,
            cls.color_attribute_black,
        ) = cls.color_attribute.value_ids
        cls.mouse_template = cls.env['product.template'].create({
            'name': 'Ergonomic Mouse',
            'list_price': 79.0,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set([
                    cls.color_attribute_white.id,
                    cls.color_attribute_black.id,
                ])],
            })],
        })
        (
            cls.mouse_white,
            cls.mouse_black,
        ) = cls.products = cls.mouse_template.product_variant_ids
        cls.mouse_white.write({
            'code': 'MAGIC-W',
            'barcode': '0195949655968',
        })
        cls.eur_currency = cls.env['res.currency'].search([
            ('name', '=', 'EUR'),
        ])
        cls.eur_currency.active = True
        cls.christmas_pricelist = cls.env['product.pricelist'].create({
            'name': 'Christmas Sales',
            'currency_id': cls.eur_currency.id,
            'item_ids': [
                Command.create({
                    'display_applied_on': '1_product',
                    'product_tmpl_id': cls.mouse_template.id,
                    'compute_price': 'percentage',
                    'percent_price': 10.0,
                    'date_start': datetime(2024, 12, 1, 0, 0),
                    'date_end': datetime(2024, 12, 31, 23, 59),
                })
            ]
        })

@tagged("post_install", "-at_install")
class TestProductGMCFeed(TestProductGMCCommon):
    

    