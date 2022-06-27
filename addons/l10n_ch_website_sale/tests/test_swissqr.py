# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

from odoo.tools.misc import mod10r

CH_IBAN = 'CH15 3881 5158 3845 3843 7'
QR_IBAN = 'CH21 3080 8001 2345 6782 7'

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSwissQRWebsit(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_ch.l10nch_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def setUp(self):
        super(TestSwissQRWebsit, self).setUp()
        # Activate SwissQR in Swiss invoices
        self.env['ir.config_parameter'].create(
            {'key': 'l10n_ch.print_qrcode', 'value': '1'}
        )
        self.customer = self.env['res.partner'].create(
            {
                "name": "Partner",
                "street": "Route de Berne 41",
                "street2": "",
                "zip": "1000",
                "city": "Lausanne",
                "country_id": self.env.ref("base.ch").id,
            }
        )
        self.env.user.company_id.partner_id.write(
            {
                "street": "Route de Berne 88",
                "street2": "",
                "zip": "2000",
                "city": "Neuchâtel",
                "country_id": self.env.ref('base.ch').id,
            }
        )
        self.product = self.env['product.product'].create({
            'name': 'Customizable Desk',
        })


    def create_account(self, number):
        """ Generates a test res.partner.bank. """
        return self.env['res.partner.bank'].create(
            {
                'acc_number': number,
                'partner_id': self.env.user.company_id.partner_id.id,
            }
        )

    def test_qq(self):
        qriban_account = self.create_account(QR_IBAN)
        self.assertTrue(qriban_account.l10n_ch_qr_iban)
        order = self.env['sale.order'].create(
            {
            'name' : "S00001",
            'partner_id': self.env['res.partner'].search([("name", '=', 'Partner')])[0].id

            }
        )
        self.env['sale.order.line'].create(
            {
            'order_id' : order.id,
            'product_id': self.env['product.product'].search([('name', '=', 'Customizable Desk')])[0].id,
            'price_unit': 100,
            }
        )
        acquirer = self.env['payment.acquirer'].create({
            'name': 'Test',
        })
        pt = self.env['payment.transaction'].create(
            {
                'acquirer_id': acquirer.id,
                'sale_order_ids' : [order.id],
                'partner_id': self.env['res.partner'].search([("name", '=', 'Partner')])[0].id,
                'amount': 100,
                'currency_id': self.env.company.currency_id.id,
            }
        )
        pt._set_pending()
        if re.match(r'^(\d{2,27})$', order.reference):
            assert(order.reference == mod10r(order.reference[:-1]))
        else:
            assert(False)
