# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from contextlib import contextmanager
import io
from PIL import Image

from odoo.fields import Command
from odoo.tools import lazy

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.product.tests.common import ProductCommon
from odoo.addons.http_routing.tests.common import MockRequest as websiteMockRequest
from odoo.addons.website_sale.models.website import (
    CART_SESSION_CACHE_KEY,
    FISCAL_POSITION_SESSION_CACHE_KEY,
    PRICELIST_SESSION_CACHE_KEY,
    PRICELIST_SELECTED_SESSION_CACHE_KEY,
)


@contextmanager
def MockRequest(
    *args,
    sale_order_id=None,
    website_sale_current_pl=None,
    fiscal_position_id=None,
    website_sale_selected_pl_id=None,
    **kwargs,
):
    with websiteMockRequest(*args, **kwargs) as request:
        if sale_order_id is not None:
            request.session[CART_SESSION_CACHE_KEY] = sale_order_id
        request.cart = lazy(request.website._get_and_cache_current_cart)

        if website_sale_current_pl is not None:
            request.session[PRICELIST_SESSION_CACHE_KEY] = website_sale_current_pl
        request.pricelist = lazy(request.website._get_and_cache_current_pricelist)

        if website_sale_selected_pl_id is not None:
            request.session[PRICELIST_SELECTED_SESSION_CACHE_KEY] = website_sale_selected_pl_id

        if fiscal_position_id is not None:
            request.session[FISCAL_POSITION_SESSION_CACHE_KEY] = fiscal_position_id
        request.fiscal_position = lazy(request.website._get_and_cache_current_fiscal_position)

        yield request


class WebsiteSaleCommon(ProductCommon, DeliveryCommon):
    # Not based on SaleCommon as there is no need for SalesTeamCommon nor standard SaleCommon data

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env.company.website_id
        if not cls.website:
            cls.website = cls.env['website'].create({
                'name': 'Test Website',
                'company_id': cls.env.company.id,
            })

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

        cls.country_be = cls.quick_ref('base.be')
        cls.country_us = cls.quick_ref('base.us')
        cls.country_us_state_id = cls.env['ir.model.data']._xmlid_to_res_id('base.state_us_39')
        cls.dummy_partner_address_values = {
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': cls.country_us.id,
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
        """ Override of `delivery` to auto-publish test delivery methods. """
        return super()._prepare_carrier(product, website_published=website_published, **values)

    @classmethod
    def _create_product(cls, **kwargs):
        """ Override of `product` to auto-publish test products by default. """
        if 'website_published' not in kwargs:
            kwargs['website_published'] = True
        return super()._create_product(**kwargs)

    @classmethod
    def _create_public_category(cls, list_vals):
        """Create a hierarchical chain of `public.product.category`.

        For example::

            # Furnitures / Sofas
            self._create_public_category([
                {'name': 'Furnitures'}, {'name': 'Sofas'}
            ])

        :return: The created categories.
        :rtype: public.product.category
        """
        categs = cls.env['product.public.category'].create(list_vals)
        for i in range(0, len(categs) - 1):
            categs[i].parent_id = categs[i + 1]
        return categs

    @classmethod
    def _create_image(cls, color):
        f = io.BytesIO()
        Image.new('RGB', (1920, 1080), color).save(f, 'JPEG')
        f.seek(0)
        return base64.b64encode(f.read())
