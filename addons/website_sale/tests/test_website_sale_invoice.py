# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('-at_install', 'post_install')
class TestWebsiteSaleInvoice(AccountPaymentCommon, SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env['website'].create({
            'name': 'Test Website'
        })

    def test_automatic_invoice_website_id(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Create SO on Test Website
        self.sale_order.website_id = self.website.id

        # Create the payment
        self.amount = self.sale_order.amount_total
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._post_process()

        self.assertEqual(self.sale_order.website_id.id, self.website.id)
        self.assertEqual(self.sale_order.invoice_ids.website_id.id, self.website.id)
