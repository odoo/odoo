from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon
from odoo import Command
from odoo.tests import tagged

from freezegun import freeze_time

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIInvoiceDocuments(TestMxEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['product.pricelist'].search([]).unlink()
        cls.env.user.groups_id |= cls.env.ref('sales_team.group_sale_salesman')

    @freeze_time('2017-02-01')
    def test_invoice_cancellation_01_from_sale_orders(self):
        """ Test the cancellation with reason '01' for an invoice linked to a sale orders.
        Most of the business flow is already tested in l10n_mx_edi so this test will only focus
        the fields on sale orders.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_mx.id,
            'l10n_mx_edi_payment_method_id': self.env.ref('l10n_mx_edi.payment_method_efectivo').id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 3,
            })],
        })
        sale_order.action_confirm()
        self.assertRecordValues(sale_order, [{'invoice_status': "to invoice"}])

        invoice = sale_order._create_invoices()
        invoice.action_post()
        self.assertRecordValues(sale_order, [{
            'invoice_status': "invoiced",
            'invoice_ids': invoice.ids,
        }])
        self.assertRecordValues(sale_order.order_line, [{'qty_invoiced': 3}])

        # Sign the invoice.
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Create a new invoice cancelling the current one.
        action_results = self.env['l10n_mx_edi.invoice.cancel'] \
            .with_context(invoice.button_request_cancel()['context']) \
            .create({}) \
            .action_create_replacement_invoice()
        new_invoice = self.env['account.move'].browse(action_results['res_id'])

        # Change the quantity and sign the new invoice.
        # The sale order is invoiced by 2 invoices but only the original one is used for computation
        # until its cancellation.
        new_invoice.invoice_line_ids.quantity = 2
        new_invoice.action_post()
        with self.with_mocked_pac_sign_success():
            new_invoice._l10n_mx_edi_cfdi_invoice_try_send()
        invoice.invalidate_recordset(fnames=['l10n_mx_edi_cfdi_cancel_id'])
        self.assertRecordValues(sale_order, [{
            'invoice_status': "invoiced",
            'invoice_ids': (invoice + new_invoice).ids,
        }])
        self.assertRecordValues(sale_order.order_line, [{'qty_invoiced': 3}])

        # Cancel the invoice.
        # The sale order considers only the cancel invoice now.
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(invoice.button_request_cancel()['context'])\
                .create({})\
                .action_cancel_invoice()
        self.assertRecordValues(sale_order, [{
            'invoice_status': "to invoice",
            'invoice_ids': (invoice + new_invoice).ids,
        }])
        self.assertRecordValues(sale_order.order_line, [{'qty_invoiced': 2}])

    @freeze_time('2017-02-01')
    def test_invoice_cancellation_01_from_sale_orders_in_locked_period(self):
        """
        Test that a compute of invoiced_qty is triggered after a cfdi state change
        """
        with freeze_time('2017-02-01'):
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_mx.id,
                'l10n_mx_edi_payment_method_id': self.env.ref('l10n_mx_edi.payment_method_efectivo').id,
                'order_line': [Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                })],
            })
            sale_order.action_confirm()

        with freeze_time('2017-01-31'):
            invoice = sale_order._create_invoices()
            invoice.action_post()
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

        lock_date_wizard = self.env['account.change.lock.date'].create({
            'fiscalyear_lock_date': '2017-01-31',
        })
        lock_date_wizard.change_lock_date()

        action_results = self.env['l10n_mx_edi.invoice.cancel'] \
            .with_context(invoice.button_request_cancel()['context']) \
            .create({}) \
            .action_create_replacement_invoice()

        with freeze_time('2017-02-01'):
            new_invoice = self.env['account.move'].browse(action_results['res_id'])
            new_invoice.action_post()
            with self.with_mocked_pac_sign_success():
                new_invoice._l10n_mx_edi_cfdi_invoice_try_send()
            invoice.invalidate_recordset(fnames=['l10n_mx_edi_cfdi_cancel_id'])

            credit_note_wizard = self.env['account.move.reversal']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({
                    'reason': 'refund',
                    'journal_id': invoice.journal_id.id,
                })
            credit_note_wizard.refund_moves()
        reversal_move = self.env['account.move'].browse(credit_note_wizard.refund_moves()['res_id'])
        reversal_move.action_post()

        self.env.invalidate_all()
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(**invoice.button_request_cancel()['context'])\
                .create({})\
                .action_cancel_invoice()

        self.assertRecordValues(sale_order.order_line, [{'qty_invoiced': 0.0}])
