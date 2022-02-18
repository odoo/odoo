# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form

from odoo.tools import html2plaintext

@common.tagged('post_install', '-at_install')
class TestSaleMrpInvoices(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_by_lot = cls.env['product.product'].create({
            'name': 'Product By Lot',
            'type': 'product',
            'tracking': 'lot',
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.lot = cls.env['stock.lot'].create({
            'name': 'LOT0001',
            'product_id': cls.product_by_lot.id,
            'company_id': cls.env.company.id,
        })
        cls.env['stock.quant']._update_available_quantity(cls.product_by_lot, cls.stock_location, 10, lot_id=cls.lot)

        cls.tracked_kit = cls.env['product.product'].create({
            'name': 'Simple Kit',
            'type': 'consu',
        })
        cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.tracked_kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': cls.product_by_lot.id,
                'product_qty': 1,
            })]
        })
        cls.partner = cls.env.ref('base.res_partner_1')

    def test_deliver_and_invoice_tracked_components(self):
        """
        Suppose the lots are printed on the invoices.
        The user sells a kit that has one tracked component.
        The lot of the delivered component should be on the invoice.
        """
        display_lots = self.env.ref('stock_account.group_lot_on_invoice')
        display_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, display_lots.id), (4, display_uom.id)]})

        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'name': self.tracked_kit.name, 'product_id': self.tracked_kit.id, 'product_uom_qty': 1}),
            ],
        })
        so.action_confirm()

        action = so.picking_ids.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()

        invoice = so._create_invoices()
        invoice.action_post()

        html = self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html)
        self.assertRegex(text, r'Product By Lot\n1.00Units\nLOT0001', "There should be a line that specifies 1 x LOT0001")
