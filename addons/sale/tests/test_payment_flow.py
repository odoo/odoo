# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import JsonRpcException, tagged
from odoo.tools import mute_logger

from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.sale.tests.common import SaleCommon


@tagged('-at_install', 'post_install')
class TestSalePayment(AccountPaymentCommon, MailCase, PaymentHttpCommon, SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Replace PaymentCommon defaults by SaleCommon ones
        cls.currency = cls.sale_order.currency_id
        cls.partner = cls.sale_order.partner_invoice_id

        cls.provider.journal_id.inbound_payment_method_line_ids.filtered(
            lambda l: l.payment_provider_id == cls.provider
        ).payment_account_id = cls.inbound_payment_method_line.payment_account_id

        cls.sale_order.require_payment = True

    @mute_logger('odoo.http', 'werkzeug')
    def test_payment_amount_must_not_be_less_than_prepayment_amount(self):
        """ Test that accessing the portal page with a payment amount below prepayment amount raises
        an error. """
        res = self._make_http_get_request(f'/my/orders/{self.sale_order.id}', params={
            'access_token': self.sale_order._portal_ensure_token(), 'payment_amount': 1
        })
        self.assertEqual(res.status_code, 404)

    def test_is_down_payment_when_prepayment_amount_is_less_than_order_total(self):
        """Test that we are in the downpayment case when the prepayment amount is less than the
        order total."""
        self.sale_order.prepayment_percent = 0.5
        self.assertTrue(CustomerPortal()._determine_is_down_payment(
            self.sale_order, 'whatever', None
        ))

    def test_is_not_down_payment_when_prepayment_amount_equals_order_total(self):
        """Test that we are not in the downpayment case when the prepayment amount equals the order
        total."""
        self.sale_order.prepayment_percent = 1.0
        self.assertFalse(CustomerPortal()._determine_is_down_payment(
            self.sale_order, 'whatever', None
        ))

    def test_is_down_payment_when_link_amount_is_less_than_order_total(self):
        """Test that we are in the downpayment case when the link amount is less than the order
        total."""
        self.assertTrue(CustomerPortal()._determine_is_down_payment(
            self.sale_order, 'whatever', self.sale_order.amount_total * 0.5
        ))

    def test_is_not_down_payment_when_link_amount_equals_order_total(self):
        """Test that we are not in the downpayment case when the link amount equals the order total.
        """
        self.assertFalse(CustomerPortal()._determine_is_down_payment(
            self.sale_order, 'whatever', self.sale_order.amount_total
        ))

    def test_downpayment_amount_equals_link_amount_when_higher_than_prepayment_amount(self):
        """Test that the payment link's amount is used for the transaction when that amount is
        higher than the prepayment amount and the user chose to pay a down payment."""
        self.sale_order.prepayment_percent = 0.5  # This should be ignored when the link is higher.
        link_amount = self.sale_order.amount_total * 0.7
        with MockRequest(self.env):
            tx_values = CustomerPortal()._get_payment_values(
                self.sale_order, is_down_payment=True, payment_amount=link_amount
            )
        self.assertEqual(tx_values['amount'], link_amount)

    def test_downpayment_amount_equals_prepayment_amount_when_less_than_order_total(self):
        """Test that the payment link's amount is used for the transaction when that amount is
        higher than the prepayment amount and the user chose to pay a down payment."""
        self.sale_order.prepayment_percent = 0.5
        with MockRequest(self.env):
            tx_values = CustomerPortal()._get_payment_values(
                self.sale_order, is_down_payment=True, payment_amount=self.sale_order.amount_total
            )
        self.assertEqual(tx_values['amount'], self.sale_order._get_prepayment_required_amount())

    def test_downpayment_amount_equals_prepayment_amount_when_no_link_amount(self):
        """Test that the prepayment amount is used for the transaction when no payment amount is
        specified in the link and the user chose to pay a down payment."""
        self.sale_order.prepayment_percent = 0.5
        with MockRequest(self.env):
            tx_values = CustomerPortal()._get_payment_values(
                self.sale_order, is_down_payment=True, payment_amount=None
            )
        prepayment_amount = self.sale_order._get_prepayment_required_amount()
        self.assertEqual(tx_values['amount'], prepayment_amount)

    def test_payment_amount_equals_link_amount_when_order_is_confirmed(self):
        """Test that the payment link's amount is used for the transaction when the order is
        confirmed."""
        self.sale_order.action_confirm()
        payment_amount = self.sale_order.amount_total * 0.5
        with MockRequest(self.env):
            tx_values = CustomerPortal()._get_payment_values(
                self.sale_order, is_down_payment=False, payment_amount=payment_amount
            )
        self.assertEqual(tx_values['amount'], payment_amount)

    def test_payment_amount_equals_order_total_when_no_link_amount_and_order_is_confirmed(self):
        """Test that the order total is used for the transaction when no payment amount is specified
        in the link and the order is confirmed."""
        self.sale_order.action_confirm()
        with MockRequest(self.env):
            tx_values = CustomerPortal()._get_payment_values(
                self.sale_order, is_down_payment=False, payment_amount=None
            )
        self.assertEqual(tx_values['amount'], self.sale_order.amount_total)

    def test_full_amount_equals_order_total(self):
        """Test that the order total is used for the transaction when the user chose to pay the full
        amount. """
        self.sale_order.prepayment_percent = 0.5  # This should not impact the 'full amount' option.
        with MockRequest(self.env):
            tx_values = CustomerPortal()._get_payment_values(
                self.sale_order,
                is_down_payment=False,
                payment_amount=self.sale_order._get_prepayment_required_amount()
            )
        self.assertEqual(tx_values['amount'], self.sale_order.amount_total)

    def test_confirmed_transactions_comfirms_so_with_multiple_transaction(self):
        """ Test that a confirmed transaction confirms a SO even if one or more non-confirmed
        transactions are linked. """
        # Create the payment
        self.amount = self.sale_order.amount_total
        self._create_transaction(
            flow='redirect',
            sale_order_ids=[self.sale_order.id],
            state='draft',
            reference='Test Transaction Draft 1',
        )
        self._create_transaction(
            flow='redirect',
            sale_order_ids=[self.sale_order.id],
            state='draft',
            reference='Test Transaction Draft 2',
        )
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        tx._post_process()

        self.assertEqual(self.sale_order.state, 'sale')

    def test_auto_confirm_and_auto_invoice(self):
        """
        Assuming that the automatic invoice setting is activated, we expect
        that after the payment is post processed:
        - invoice created
        - SO confirmed
        - Two emails sent: SO confirmation and default invoice email template
        """
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Create the payment
        self.amount = self.sale_order.amount_total
        self.partner.email = 'customer@example.com'  # make sure partner on SO has email set
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with (
            mute_logger('odoo.addons.sale.models.payment_transaction'),
            self.mock_mail_gateway(),
        ):
            tx._post_process()

        self.assertEqual(self.sale_order.state, 'sale')
        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)
        self.assertEqual(len(self._new_mails), 2)
        self.assertTrue(self._new_mails.filtered(lambda x: 'Invoice' in x.subject))

    def test_auto_confirm_and_auto_invoice_custom_mail_template(self):
        """
        Assuming that the automatic invoice setting is activated and a custom
        email template for invoicing was selected, we expect that after the
        payment is post processed:
        - invoice created
        - SO confirmed
        - Two emails sent: SO confirmation and invoice email using the custom template
        """
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        custom_template = self.env['mail.template'].create({
            'name': 'Custom Test Invoice Template',
            'model_id': self.env.ref('account.model_account_move').id,
            'subject': 'Your Custom Template',
            'partner_to': '{{ object.partner_id.id }}',
            'email_from': '{{ (object.invoice_user_id.email_formatted or object.company_id.email_formatted or user.email_formatted) }}',
        })
        self.env['ir.config_parameter'].set_param('sale.default_invoice_email_template', custom_template.id)

        # Create the payment
        self.amount = self.sale_order.amount_total
        self.partner.email = 'customer@example.com'  # make sure partner on SO has email set
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with (
            mute_logger('odoo.addons.sale.models.payment_transaction'),
            self.mock_mail_gateway(),
        ):
            tx._post_process()

        self.assertEqual(self.sale_order.state, 'sale')
        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)
        self.assertEqual(len(self._new_mails), 2)
        self.assertTrue(self._new_mails.filtered(lambda x: 'Your Custom Template' in x.subject))

    def test_auto_confirm_and_auto_invoice_custom_mail_template_unlinked(self):
        """
        Assuming that the automatic invoice setting is activated and a custom
        email template for invoicing was selected. If the custom email template
        gets unlinked, the system parameter still stores the id, but code
        should fall back to default invoice email template. We expect that after the
        payment is post processed:
        - invoice created
        - SO confirmed
        - Two emails sent: SO confirmation and invoice email using the DEFAULT template
        """
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        custom_template = self.env['mail.template'].create({
            'name': 'Custom Test Invoice Template',
            'model_id': self.env.ref('account.model_account_move').id,
            'subject': 'Your Custom Template',
            'partner_to': '{{ object.partner_id.id }}',
            'email_from': '{{ (object.invoice_user_id.email_formatted or object.company_id.email_formatted or user.email_formatted) }}',
        })
        self.env['ir.config_parameter'].set_param('sale.default_invoice_email_template', custom_template.id)
        custom_template.unlink()

        # Create the payment
        self.amount = self.sale_order.amount_total
        self.partner.email = 'customer@example.com'  # make sure partner on SO has email set
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with (
            mute_logger('odoo.addons.sale.models.payment_transaction'),
            self.mock_mail_gateway(),
        ):
            tx._post_process()

        self.assertEqual(self.sale_order.state, 'sale')
        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)
        self.assertEqual(len(self._new_mails), 2)
        self.assertTrue(self._new_mails.filtered(lambda x: 'Invoice' in x.subject))

    def test_auto_done_and_auto_invoice(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')
        # Lock the sale orders when confirmed
        self.group_user.implied_ids += self.env.ref('sale.group_auto_done_setting')

        # Create the payment
        self.amount = self.sale_order.amount_total
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._post_process()

        self.assertEqual(self.sale_order.state, 'sale')
        self.assertTrue(self.sale_order.locked)
        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)
        self.assertTrue(tx.invoice_ids.is_move_sent)

    def test_so_partial_payment_no_invoice(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Create the payment
        self.amount = self.sale_order.amount_total / 10.
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._post_process()

        self.assertEqual(self.sale_order.state, 'draft')
        self.assertFalse(tx.invoice_ids)
        self.assertFalse(self.sale_order.invoice_ids)

    def test_already_confirmed_so_payment(self):
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Confirm order before payment
        self.sale_order.action_confirm()

        # Create the payment
        self.amount = self.sale_order.amount_total
        tx = self._create_transaction(flow='redirect', sale_order_ids=[self.sale_order.id], state='done')
        tx._post_process()

        self.assertTrue(tx.invoice_ids)
        self.assertTrue(self.sale_order.invoice_ids)

    def test_invoice_is_final(self):
        """Test that invoice generated from a payment are always final"""
        # Set automatic invoice
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        # Create the payment
        self.amount = self.sale_order.amount_total
        tx = self._create_transaction(
            flow='redirect',
            sale_order_ids=[self.sale_order.id],
            state='done',
        )
        with mute_logger('odoo.addons.sale.models.payment_transaction'), patch(
            'odoo.addons.sale.models.sale_order.SaleOrder._create_invoices',
            return_value=self.env['account.move']
        ) as _create_invoices_mock:
            tx._post_process()

        self.assertTrue(_create_invoices_mock.call_args.kwargs['final'])

    def test_linked_transactions_when_invoicing(self):
        self.provider.support_manual_capture = 'partial'
        partial_amount = self.sale_order.amount_total - 2

        partial_tx_done = self._create_transaction(
            flow='direct',
            amount=partial_amount,
            sale_order_ids=[self.sale_order.id],
            state='done',
            reference='partial_tx_done',
        )
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            partial_tx_done._post_process()
        partial_tx_pending = self._create_transaction(
            flow='direct',
            amount=2,
            sale_order_ids=[self.sale_order.id],
            state='pending',
            reference='partial_tx_pending',
        )
        self.assertTrue(partial_tx_done.payment_id, msg="Account payment should have been created.")
        msg = "The created account payment shouldn't be reconciled as there are no invoice yet."
        self.assertFalse(partial_tx_pending.payment_id.is_reconciled, msg=msg)

        # Add some noisy transactions
        self._create_transaction(
            flow='direct', sale_order_ids=[self.sale_order.id], state='draft', reference='draft_tx'
        )
        self._create_transaction(
            flow='direct', sale_order_ids=[self.sale_order.id], state='error', reference='error_tx'
        )
        self._create_transaction(
            flow='direct', sale_order_ids=[self.sale_order.id], state='cancel', reference='cncl_tx'
        )

        msg = "The sale order should be linked to 5 transactions."
        self.assertEqual(len(self.sale_order.transaction_ids), 5, msg=msg)

        self.sale_order.action_confirm()
        self.sale_order._create_invoices()

        self.assertEqual(len(self.sale_order.invoice_ids), 1, msg="1 invoice should be created.")

        first_invoice = self.sale_order.invoice_ids
        linked_txs = first_invoice.transaction_ids
        msg = "The newly created invoice should be linked to the done and pending transactions."
        self.assertEqual(len(linked_txs), 2, msg=msg)
        expected_linked_tx = (partial_tx_done, partial_tx_pending)
        self.assertTrue(all(tx in expected_linked_tx for tx in linked_txs), msg=msg)
        msg = "The payment shouldn't be reconciled yet."
        self.assertFalse(partial_tx_done.payment_id.is_reconciled, msg=msg)

        partial_tx_done._post_process()

        msg = "The payment should now be reconciled."
        self.assertTrue(partial_tx_done.payment_id.is_reconciled, msg=msg)

        self.sale_order.order_line[0].product_uom_qty += 2
        self.sale_order._create_invoices()

        second_invoice = self.sale_order.invoice_ids - first_invoice
        msg = "The newly created invoice should only be linked to the pending transaction."
        self.assertEqual(len(second_invoice.transaction_ids), 1, msg=msg)
        self.assertEqual(second_invoice.transaction_ids.state, 'pending', msg=msg)

    def test_downpayment_confirm_sale_order_sufficient_amount(self):
        """Paying down payments can confirm an order if amount is enough."""
        self.sale_order.prepayment_percent = 0.1
        order_amount = self.sale_order.amount_total

        tx = self._create_transaction(
            flow='direct',
            amount=order_amount * self.sale_order.prepayment_percent,
            sale_order_ids=[self.sale_order.id],
            state='done',
        )
        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._post_process()

        self.assertTrue(self.sale_order.state == 'sale')

    def test_downpayment_automatic_invoice(self):
        """
        Down payment invoices should be created when a down payment confirms
        the order and automatic invoice is checked.
        """
        self.sale_order.prepayment_percent = 0.2
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        tx = self._create_transaction(
            flow='direct',
            amount=self.sale_order.amount_total * self.sale_order.prepayment_percent,
            sale_order_ids=[self.sale_order.id],
            state='done')

        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx._post_process()

        invoice = self.sale_order.invoice_ids
        self.assertTrue(len(invoice) == 1)
        self.assertTrue(invoice.line_ids[0].is_downpayment)

    @mute_logger('odoo.http')
    def test_transaction_route_rejects_unexpected_kwarg(self):
        url = self._build_url(f'/my/orders/{self.sale_order.id}/transaction')
        route_kwargs = {
            'access_token': self.sale_order._portal_ensure_token(),
            'partner_id': self.partner.id,  # This should be rejected.
        }
        with self.assertRaises(JsonRpcException, msg='odoo.exceptions.ValidationError'):
            self.make_jsonrpc_request(url, route_kwargs)

    def test_partial_payment_confirm_order(self):
        """
        Test that a sale order can be confirmed through partial payments and that
        correct mails are sent each time.
        """
        self.amount = self.sale_order.amount_total / 2

        with patch(
            'odoo.addons.sale.models.sale_order.SaleOrder._send_order_notification_mail',
        ) as notification_mail_mock:
            tx_pending = self._create_transaction(
                flow='direct',
                sale_order_ids=[self.sale_order.id],
                state='pending',
                reference='Test Transaction Draft 1',
            )

            self.assertEqual(self.sale_order.state, 'draft')

            tx_pending._set_done()
            tx_pending._post_process()

            self.assertEqual(notification_mail_mock.call_count, 1)
            notification_mail_mock.assert_called_once_with(
                self.env.ref('sale.mail_template_sale_payment_executed'))
            self.assertEqual(self.sale_order.state, 'draft')
            self.assertEqual(self.sale_order.amount_paid, self.amount)

            tx_done = self._create_transaction(
                flow='direct',
                sale_order_ids=[self.sale_order.id],
                state='done',
                reference='Test Transaction Draft 2',
            )
            tx_done._post_process()

            self.assertEqual(notification_mail_mock.call_count, 2)
            order_confirmation_mail_template_id = int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("sale.default_confirmation_template", self.env.ref("sale.mail_template_sale_confirmation").id)
            )
            notification_mail_mock.assert_called_with(self.env["mail.template"].browse(order_confirmation_mail_template_id))
            self.assertEqual(self.sale_order.state, 'sale')

    def test_automatic_invoice_mail_author(self):
        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', 'True')

        portal_user = self.env['res.users'].create({
            'name': 'Portal Customer',
            'login': 'portal@test.com',
            'email': 'portal@test.com',
            'partner_id': self.partner_a.id,
            'group_ids': [(6, 0, [self.env.ref('base.group_portal').id])],
        })
        portal_user.partner_id.invoice_sending_method = 'email'

        sale_order = self.env['sale.order'].with_user(portal_user).sudo().create({
            'partner_id': portal_user.partner_id.id,
            'user_id': self.sale_user.id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })

        self.amount = sale_order.amount_total
        tx = self._create_transaction(
            flow='redirect',
            sale_order_ids=[sale_order.id],
            state='done'
        )

        with mute_logger('odoo.addons.sale.models.payment_transaction'):
            tx.with_user(portal_user).sudo()._post_process()

        # Verify invoice was created and sent successfully
        invoice = sale_order.invoice_ids[0]
        self.assertTrue(invoice.is_move_sent, "Invoice should be marked as sent")
        invoice_sent_mail = invoice.message_ids[0]
        self.assertTrue(invoice_sent_mail.author_id.id not in invoice_sent_mail.notified_partner_ids.ids)

    def test_refund_message_author_is_logged_in_user_for_sale_order(self):
        """Ensure that the chatter message author is the user processing the refund."""
        self.provider.support_refund = 'full_only'

        tx = self._create_transaction(
            'redirect',
            sale_order_ids=[self.sale_order.id],
            state='done',
        )
        tx._post_process()

        with patch.object(
            self.env.registry['mail.thread'], 'message_post', autospec=True
        ) as message_post_mock:
            tx.action_refund()
            author_id = message_post_mock.call_args[1].get("author_id")

        self.assertEqual(author_id, self.user.partner_id.id)
