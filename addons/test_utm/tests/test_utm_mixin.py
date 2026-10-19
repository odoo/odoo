# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests.common import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.utm.tests.common import TestUTMCommon


@tagged('post_install', '-at_install', 'utm')
class TestUTMMixin(TestUTMCommon, HttpCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if cls.env.user.has_group('sales_team.group_sale_salesman'):
            # see utm.mixin "default_get": salesman bypasses the flow, we don't want that
            cls.user_demo.group_ids -= cls.env.ref('sales_team.group_sale_salesman')

        cls.test_mailing = cls.env['test.utm.mailing'].create({'subject': 'XMas Promo'})

    def test_utm_mixin(self):
        """ This test simulates a real HTTP request with UTM cookies and makes sure everything is
        properly set on the resulting record.

        This includes:
        - The utm.source, based on its unique name
        - The utm.medium, based on its unique name
        - The utm.campaign, based on its unique name
        - The utm_reference field, towards its originating record

        See: utm.mixin#default_get """

        self.authenticate('demo', 'demo')

        # do not assign UTM cookies, UTM values should be blank
        test_so = self._create_fake_sale_order()
        self.assertFalse(bool(test_so.source_id))
        self.assertFalse(bool(test_so.medium_id))
        self.assertFalse(bool(test_so.campaign_id))
        self.assertFalse(bool(test_so.utm_reference))

        # assign proper UTM cookies, UTM values should be set
        self.opener.cookies.update({
            'odoo_utm_source': 'Test Source',
            'odoo_utm_medium': 'Test Medium',
            'odoo_utm_campaign': 'Test Campaign',
            'odoo_utm_reference': f'test.utm.mailing,{self.test_mailing.id}',
        })

        test_so = self._create_fake_sale_order()
        self.assertEqual(test_so.source_id, self.utm_source)
        self.assertEqual(test_so.medium_id, self.utm_medium)
        self.assertEqual(test_so.campaign_id, self.utm_campaign)
        self.assertEqual(test_so.utm_reference, self.test_mailing)

        # assign non-existing UTM record in cookies, should auto-create
        self.assertEqual(self.env['utm.source'].search_count([('name', '=', 'UTM Source New')]), 0)
        self.assertEqual(self.env['utm.medium'].search_count([('name', '=', 'UTM Medium New')]), 0)
        self.assertEqual(self.env['utm.campaign'].search_count([('name', '=', 'UTM Campaign New')]), 0)

        self.opener.cookies.update({
            'odoo_utm_source': 'UTM Source New',
            'odoo_utm_medium': 'UTM Medium New',
            'odoo_utm_campaign': 'UTM Campaign New',
            'odoo_utm_reference': 'invalid_reference,77',
        })
        test_so = self._create_fake_sale_order()
        self.assertEqual(test_so.source_id.name, 'UTM Source New')
        self.assertEqual(test_so.medium_id.name, 'UTM Medium New')
        self.assertEqual(test_so.campaign_id.name, 'UTM Campaign New')
        self.assertFalse(test_so.utm_reference)

    def _create_fake_sale_order(self):
        sale_order_id = self.url_open(
            '/web/dataset/call_kw/test.utm.sale.order/create',
            data=json.dumps({
                'id': 0,
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'model': 'test.utm.sale.order',
                    'method': 'create',
                    'args': [{'amount': 500}],
                    'kwargs': {},
                }
            }),
            headers={
                "Content-Type": "application/json",
            }
        ).json()['result']

        return self.env['test.utm.sale.order'].browse(sale_order_id)
