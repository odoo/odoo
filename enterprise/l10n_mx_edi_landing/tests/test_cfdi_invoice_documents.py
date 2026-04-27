from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIInvoiceDocumentsLanding(TestMxEdiCommon):

    def test_make_cfdi_report_carry_over_canceled_invoice(self):
        """ Test that after a cfdi cancellation of the parent invoice the child invoice still gets the lot values. """

        product = self.env['product.product'].create({
            'name': 'product_serial',
            'type': 'consu',
            'is_storable': True,
            'tracking': 'serial',
            'unspsc_code_id': self.env.ref('product_unspsc.unspsc_code_12352106').id,
        })

        serial = self.env['stock.lot'].create({
            'name': 'serial',
            'product_id': product.id,
        })
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
        stock_loc = wh.lot_stock_id
        self.env["stock.quant"]._update_available_quantity(product, stock_loc, 1.0, lot_id=serial)

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_mx.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 1.0,
            })]
        })

        sale_order.action_confirm()
        sale_order.picking_ids.move_ids.picked = True
        sale_order.picking_ids.move_ids.quantity = 1.0
        sale_order.picking_ids.button_validate()

        with self.mx_external_setup(self.frozen_today):
            invoice = sale_order._create_invoices()
            invoice.action_post()
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

        invoice_cancelled_lot = invoice._get_invoiced_lot_values()

        with self.with_mocked_pac_cancel_success():
            action_results = self.env['l10n_mx_edi.invoice.cancel'] \
                .with_context(invoice.button_request_cancel()['context']) \
                .create({'cancellation_reason': '01'}) \
                .action_create_replacement_invoice()
        new_invoice = self.env['account.move'].browse(action_results['res_id'])

        with self.with_mocked_pac_sign_success():
            new_invoice.action_post()
            new_invoice._l10n_mx_edi_cfdi_invoice_try_send()

        invoice.l10n_mx_edi_cfdi_uuid = '00000000-0000-0000-0000-000000000001'
        new_invoice_cancelled_lot = new_invoice._get_invoiced_lot_values()

        self.assertEqual(invoice_cancelled_lot, new_invoice_cancelled_lot)
