# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.models import Command
from odoo.tests.common import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install')
class WebsiteSaleCartPayment(PaymentCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.website = cls.env['website'].get_current_website()
        with MockRequest(cls.env, website=cls.website):
            cls.order = cls.website.sale_get_order(force_create=True)  # Create the cart to retrieve
        cls.tx = cls.env['payment.transaction'].create({
            'amount': cls.amount,
            'currency_id': cls.currency.id,
            'acquirer_id': cls.acquirer.id,
            'reference': cls.reference,
            'operation': 'online_redirect',
            'partner_id': cls.partner.id,
        })
        cls.order.write({'transaction_ids': [Command.set([cls.tx.id])]})

    def test_unpaid_orders_can_be_retrieved(self):
        """ Test that fetching sales orders linked to a payment transaction in the states 'draft',
        'cancel', or 'error' returns the orders. """
        for unpaid_order_tx_state in ('draft', 'cancel', 'error'):
            self.tx.state = unpaid_order_tx_state
            with MockRequest(self.env, website=self.website, sale_order_id=self.order.id):
                self.assertEqual(
                    self.website.sale_get_order(),
                    self.order,
                    msg=f"The transaction state '{unpaid_order_tx_state}' should not prevent "
                        f"retrieving the linked order.",
                )

    def test_paid_orders_cannot_be_retrieved(self):
        """ Test that fetching sales orders linked to a payment transaction in the states 'pending',
        'authorized', or 'done' returns an empty recordset to prevent updating the paid orders. """
        self.tx.acquirer_id.support_authorization = True
        for paid_order_tx_state in ('pending', 'authorized', 'done'):
            self.tx.state = paid_order_tx_state
            with MockRequest(self.env, website=self.website, sale_order_id=self.order.id):
                self.assertFalse(
                    self.website.sale_get_order(),
                    msg=f"The transaction state '{paid_order_tx_state}' should prevent retrieving "
                        f"the linked order.",
                )
