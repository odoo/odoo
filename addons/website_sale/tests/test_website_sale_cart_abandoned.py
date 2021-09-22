# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserPortal


@tagged('post_install', '-at_install')
class TestWebsiteSaleCartAbandoned(HttpCaseWithUserPortal):
    def setUp(self):
        res = super(TestWebsiteSaleCartAbandoned, self).setUp()
        now = datetime.utcnow()
        self.customer = self.env['res.partner'].create({
            'name': 'a',
            'email': 'a@example.com',
        })
        self.public_partner = self.env['res.partner'].create({
            'name': 'public',
            'email': 'public@example.com',
        })
        self.public_user = self.env['res.users'].create({
            'name': 'Foo', 'login': 'foo',
            'partner_id': self.public_partner.id,
        })
        self.website0 = self.env['website'].create({
            'name': 'web0',
            'cart_abandoned_delay': 1.0,  # 1 hour
        })
        self.website1 = self.env['website'].create({
            'name': 'web1',
            'cart_abandoned_delay': 0.5,  # 30 minutes
        })
        self.website2 = self.env['website'].create({
            'name': 'web2',
            'cart_abandoned_delay': 24.0,  # 1 day
            'user_id': self.public_user.id,  # specific public user
        })
        product = self.env['product.product'].create({
            'name': 'The Product'
        })
        add_order_line = [[0, 0, {
            'name': 'The Product',
            'product_id': product.id,
            'product_uom_qty': 1,
        }]]
        self.so0before = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'website_id': self.website0.id,
            'state': 'draft',
            'date_order': (now - relativedelta(hours=1)) - relativedelta(minutes=1),
            'order_line': add_order_line,
        })
        self.so0after = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'website_id': self.website0.id,
            'state': 'draft',
            'date_order': (now - relativedelta(hours=1)) + relativedelta(minutes=1),
            'order_line': add_order_line,
        })
        self.so1before = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'website_id': self.website1.id,
            'state': 'draft',
            'date_order': (now - relativedelta(minutes=30)) - relativedelta(minutes=1),
            'order_line': add_order_line,
        })
        self.so1after = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'website_id': self.website1.id,
            'state': 'draft',
            'date_order': (now - relativedelta(minutes=30)) + relativedelta(minutes=1),
            'order_line': add_order_line,
        })
        self.so2before = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'website_id': self.website2.id,
            'state': 'draft',
            'date_order': (now - relativedelta(hours=24)) - relativedelta(minutes=1),
            'order_line': add_order_line,
        })
        self.so2after = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'website_id': self.website2.id,
            'state': 'draft',
            'date_order': (now - relativedelta(hours=24)) + relativedelta(minutes=1),
            'order_line': add_order_line,
        })
        self.so2before_but_public = self.env['sale.order'].create({
            'partner_id': self.public_partner.id,
            'website_id': self.website2.id,
            'state': 'draft',
            'date_order': (now - relativedelta(hours=24)) - relativedelta(minutes=1),
            'order_line': add_order_line,
        })

        # Must behave like so1before because public partner is not the one of website1
        self.so1before_but_other_public = self.env['sale.order'].create({
            'partner_id': self.public_partner.id,
            'website_id': self.website1.id,
            'state': 'draft',
            'date_order': (now - relativedelta(minutes=30)) - relativedelta(minutes=1),
            'order_line': add_order_line,
        })

        return res

    def test_search_abandoned_cart(self):
        """Make sure the search for abandoned carts uses the delay and public partner specified in each website."""
        SaleOrder = self.env['sale.order']
        abandoned = SaleOrder.search([('is_abandoned_cart', '=', True)]).ids
        self.assertTrue(self.so0before.id in abandoned)
        self.assertTrue(self.so1before.id in abandoned)
        self.assertTrue(self.so1before_but_other_public.id in abandoned)
        self.assertTrue(self.so2before.id in abandoned)
        self.assertFalse(self.so0after.id in abandoned)
        self.assertFalse(self.so1after.id in abandoned)
        self.assertFalse(self.so2after.id in abandoned)
        self.assertFalse(self.so2before_but_public.id in abandoned)

        non_abandoned = SaleOrder.search([('is_abandoned_cart', '=', False)]).ids
        self.assertFalse(self.so0before.id in non_abandoned)
        self.assertFalse(self.so1before.id in non_abandoned)
        self.assertFalse(self.so1before_but_other_public.id in non_abandoned)
        self.assertFalse(self.so2before.id in non_abandoned)
        self.assertTrue(self.so0after.id in non_abandoned)
        self.assertTrue(self.so1after.id in non_abandoned)
        self.assertTrue(self.so2after.id in non_abandoned)
        self.assertFalse(self.so2before_but_public.id in abandoned)
