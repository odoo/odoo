# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.website.tools import MockRequest
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class WebsiteSaleCartPayment(PaymentAcquirerCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.website = cls.env['website'].get_current_website()
        with MockRequest(cls.env, website=cls.website):
            cls.order = cls.website.sale_get_order(force_create=True)  # Create the cart to retrieve

        cls.acquirer = cls.env['payment.acquirer'].create({
            'name': "Dummy Acquirer",
            'provider': 'manual',
            'state': 'test',
            'journal_id': cls.company_data['default_journal_bank'].id,
        })
        cls.tx = cls.env['payment.transaction'].create({
            'amount': 1111.11,
            'currency_id': cls.currency_euro.id,
            'acquirer_id': cls.acquirer.id,
            'reference': "Test Transaction",
            'partner_id': cls.buyer.id,
        })
        cls.order.write({'transaction_ids': [(6, 0, [cls.tx.id])]})

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
        with patch(
            'odoo.addons.payment.models.payment_acquirer.PaymentAcquirer._get_feature_support',
            return_value={'authorize': ['manual'], 'tokenize': [], 'fees': []},
        ):
            for paid_order_tx_state in ('pending', 'authorized', 'done'):
                self.tx.state = paid_order_tx_state
                with MockRequest(self.env, website=self.website, sale_order_id=self.order.id):
                    self.assertFalse(
                        self.website.sale_get_order(),
                        msg=f"The transaction state '{paid_order_tx_state}' should prevent retrieving "
                        f"the linked order.",
                    )
