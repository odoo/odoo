# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from lxml import html

from odoo.fields import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseUsersCommon, HttpCaseWithUserPortal
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestAccessRightsControllers(BaseUsersCommon, HttpCase, SaleCommon):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    def test_access_controller(self):
        private_so = self.sale_order
        portal_so = self.sale_order.copy()
        portal_so.message_subscribe(self.user_portal.partner_id.ids)

        portal_so._portal_ensure_token()
        token = portal_so.access_token

        self.authenticate(None, None)

        # Test public user can't print an order without a token
        req = self.url_open(
            url='/my/orders/%s?report_type=pdf' % portal_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 303)

        # or with a random token
        req = self.url_open(
            url='/my/orders/%s?access_token=%s&report_type=pdf' % (
                portal_so.id,
                "foo",
            ),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 303)

        # but works fine with the right token
        req = self.url_open(
            url='/my/orders/%s?access_token=%s&report_type=pdf' % (
                portal_so.id,
                token,
            ),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)

        self.authenticate(self.user_portal.login, self.user_portal.login)

        # do not need the token when logged in
        req = self.url_open(
            url='/my/orders/%s?report_type=pdf' % portal_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)

        # but still can't access another order
        req = self.url_open(
            url='/my/orders/%s?report_type=pdf' % private_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 303)


@tagged('post_install', '-at_install')
class TestSalesControllers(BaseUsersCommon, HttpCase, SaleCommon):
    def test_sales_portal_report(self):
        portal_so = self.sale_order.copy()
        portal_so.message_subscribe(self.user_portal.partner_id.ids)

        self.authenticate(None, None)

        req = self.url_open(portal_so.get_portal_url(report_type='pdf'), allow_redirects=False)
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.headers['content-disposition'], f"inline; filename*=UTF-8''Quotation_{portal_so.name}.pdf")

        req = self.url_open(portal_so.get_portal_url(report_type='pdf', download=True), allow_redirects=False)
        self.assertEqual(req.status_code, 200)
        self.assertEqual(req.headers['content-disposition'], f"attachment; filename*=UTF-8''Quotation_{portal_so.name}.pdf")


@tagged('post_install', '-at_install')
class TestSaleSignature(HttpCaseWithUserPortal):

    def test_01_portal_sale_signature_tour(self):
        """The goal of this test is to make sure the portal user can sign SO."""

        portal_user_partner = self.partner_portal
        # create a SO to be signed
        sales_order = self.env['sale.order'].create({
            'name': 'test SO',
            'partner_id': portal_user_partner.id,
            'state': 'sent',
            'require_payment': False,
        })
        self.env['sale.order.line'].create({
            'order_id': sales_order.id,
            'product_id': self.env['product.product'].create({'name': 'A product'}).id,
        })

        # must be sent to the user so he can see it
        email_act = sales_order.action_quotation_send()
        email_ctx = email_act.get('context', {})
        sales_order.with_context(**email_ctx).message_post_with_source(
            self.env['mail.template'].browse(email_ctx.get('default_template_id')),
            subtype_xmlid='mail.mt_comment',
        )

        self.start_tour("/", 'sale_signature', login="portal")

    def test_02_portal_sale_signature_modified_quotation(self):
        """The customer must not be able to sign a quotation that was modified
        after they opened it, as they would sign terms they have not seen."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_portal.id,
            'require_signature': True,
            'require_payment': False,
            'order_line': [Command.create({
                'product_id': self.env['product.product'].create({'name': 'A product'}).id,
                'price_unit': 100.0,
            })],
        })
        sale_order._portal_ensure_token()
        signature = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='

        def open_quotation():
            """Open the quotation as the customer and return the accept url."""
            self.authenticate(None, None)
            res = self.url_open(sale_order.get_portal_url())
            res.raise_for_status()
            props = html.fromstring(res.content).xpath(
                '//owl-component[@name="portal.signature_form"]/@props',
            )[0]
            return json.loads(props)['callUrl']

        accept_url = open_quotation()

        # Meanwhile, the salesperson changes the price in the backend.
        self.authenticate('admin', 'admin')
        self.make_jsonrpc_request('/web/dataset/call_kw/sale.order/write', {
            'model': 'sale.order',
            'method': 'write',
            'args': [sale_order.ids, {
                'order_line': [Command.update(sale_order.order_line.id, {'price_unit': 200.0})],
            }],
            'kwargs': {},
        })

        # The customer signs from the page they opened before the change.
        self.authenticate(None, None)
        result = self.make_jsonrpc_request(accept_url, {'name': 'Joel Willis', 'signature': signature})
        self.assertIn('error', result)
        sale_order.invalidate_recordset()
        self.assertEqual(sale_order.order_line.price_unit, 200.0)
        self.assertFalse(sale_order.signature)
        self.assertEqual(sale_order.state, 'draft')

        # Once the page is reloaded, the customer can sign the quotation.
        accept_url = open_quotation()
        result = self.make_jsonrpc_request(accept_url, {'name': 'Joel Willis', 'signature': signature})
        self.assertNotIn('error', result)
        sale_order.invalidate_recordset()
        self.assertTrue(sale_order.signature)
        self.assertEqual(sale_order.signed_by, 'Joel Willis')
        self.assertEqual(sale_order.state, 'sale')
