# -*- coding: utf-8 -*-

from unittest.mock import patch
from freezegun import freeze_time
from datetime import datetime

from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.account_payment.tests.common import AccountPaymentCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSubscriptionPaymentsAccount(AccountPaymentCommon, TestSubscriptionCommon, MockEmail):

    # Inheriting on AccountPaymentCommon is necessary because it patches _get_payment_method_information

    def test_invoice_consolidation(self):
        with patch('odoo.addons.sale_subscription.models.sale_order.SaleOrder._do_payment', wraps=self._mock_subscription_do_payment):
            self.env['ir.config_parameter'].set_param('sale_subscription.invoice_consolidation', True)
            bank_journal = self.company_data['default_journal_bank']
            new_provider = self.dummy_provider.copy({
                'name': 'New provider',
                'journal_id': bank_journal.id,
                'code': 'none',
                'state': 'test',
            })
            self.dummy_provider.unlink()
            new_provider.journal_id = bank_journal.id
            test_payment_token = self.env['payment.token'].create({
                'payment_details': 'Test',
                'partner_id': self.subscription.partner_id.id,
                'provider_id': new_provider.id,
                'payment_method_id': self.payment_method_id,
                'provider_ref': 'test'
            })

            self.subscription._onchange_sale_order_template_id()
            self.subscription.write({
                'payment_token_id':test_payment_token.id,
                'start_date': False,
                'next_invoice_date': False,
            })
            other_user = self.company_data['default_user_salesman']
            sub2 = self.subscription.copy({'payment_token_id': test_payment_token.id, 'user_id': other_user.id})  # tokens have copy=False property
            with freeze_time("2023-02-01"):
                # add a subscription intended to be removed from the recordset to make sure we don't invoice it.
                sub3 = self.subscription.copy({'payment_token_id': test_payment_token.id, 'end_date': datetime.today().date()})
                (sub2 | self.subscription | sub3).action_confirm()
                # enable tracking to test _message_auto_subscribe_followers with multiple user_id
                self.env['sale.order'].with_context(test_provider=new_provider, tracking_disable=False)._create_recurring_invoice()
                self.assertEqual(self.subscription.invoice_ids, sub2.invoice_ids)
                invoice = sub2.invoice_ids
                invoice.journal_id.type = 'bank'
                self.assertEqual(self.subscription.invoice_ids.invoice_line_ids.mapped('quantity'),
                                self.subscription.order_line.mapped('product_uom_qty') + sub2.order_line.mapped('product_uom_qty'))
                tx = self.env['payment.transaction'].search([('invoice_ids', 'in', invoice.ids)])
                tx._set_done()
                tx._create_payment()
                self.assertTrue(invoice.payment_state in ['in_payment', 'paid'])
