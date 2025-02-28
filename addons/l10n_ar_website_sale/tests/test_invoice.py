# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import tagged
from odoo.tools import mute_logger
from freezegun import freeze_time

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.sale.tests.common import SaleCommon
from odoo.addons.l10n_ar.tests.common import TestAr


@tagged('-at_install', 'post_install', 'post_install_l10n')
class TestWebsiteSaleInvoice(AccountPaymentCommon, SaleCommon, TestAr):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].create({'name': 'Test AR Website'})

    def test_website_automatic_invoice_date(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        self.frozen_today = "2025-01-24T21:10:00"
        with freeze_time(self.frozen_today, tz_offset=3):

            # Prepare values needed for AR invoice generation: Tax in all lines, and AFIP responsibility partner
            self.sale_order.order_line.write({'tax_id': self.company_data['default_tax_sale']})
            self.sale_order.partner_id = self.partner_cf
            self.sale_order.currency_id = self.env.ref('base.ARS')

            # Create SO on Test Website
            self.sale_order.website_id = self.website.id

            # Create the payment and invoices
            self.amount = self.sale_order.amount_total
            tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
            with mute_logger('odoo.addons.sale.models.payment_transaction'):
                tx.with_context(l10n_ar_invoice_skip_commit=True)._reconcile_after_done()

            invoice = self.sale_order.invoice_ids
            self.assertTrue(invoice, "Do not create the invoice")
            self.assertEqual(invoice.state, "posted", "the invoice was not posted")
            self.assertEqual(fields.Datetime.now().date().strftime("%Y-%m-%d"), '2025-01-25', "UCT should be next day")
            self.assertEqual(invoice.invoice_date.strftime('%Y-%m-%d'), '2025-01-24', "Should be AR current date")
