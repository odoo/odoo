# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.product.tests.common import ProductCommon

# from odoo.addons.website.tests.common import WebsiteCommon


class WebsiteSaleCommon(ProductCommon, DeliveryCommon):
    # Not based on SaleCommon as there is no need for SalesTeamCommon nor standard SaleCommon data

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env.company.website_id
        if not cls.website:
            pass # TODO WebsiteCommon

        cls.public_user = cls.website.user_id
        cls.public_partner = cls.public_user.partner_id

        cls.empty_cart = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'website_id': cls.website.id,
        })
        cls.cart = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'website_id': cls.website.id,
            'order_line': [
                Command.create({
                    'product_id': cls.product.id,
                    'product_uom_qty': 5.0,
                }),
                Command.create({
                    'product_id': cls.service_product.id,
                    'product_uom_qty': 12.5,
                })
            ]
        })

        # Publish tests products
        (
            cls.product
            + cls.service_product
        ).website_published = True
        cls.pricelist.website_id = cls.website

        country_be_id = cls.env['ir.model.data']._xmlid_to_res_id('base.be')
        country_us_id = cls.env['ir.model.data']._xmlid_to_res_id('base.us')
        cls.country_be = cls.env['res.country'].browse(country_be_id)
        cls.country_us = cls.env['res.country'].browse(country_us_id)
        cls.country_us_state_id = cls.env['ir.model.data']._xmlid_to_res_id('base.state_us_39')
        cls.dummy_partner_address_values = {
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': country_us_id,
            'state_id': cls.country_us_state_id,
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        }

    def _create_so(self, **values):
        default_values = {
            'partner_id': self.partner.id,
            'website_id': self.website.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                }),
            ],
        }
        return self.env['sale.order'].create(dict(default_values, **values))

    @classmethod
    def _prepare_carrier(cls, product, website_published=True, **values):
        # Publish carriers by default
        return super()._prepare_carrier(product, website_published=website_published, **values)
