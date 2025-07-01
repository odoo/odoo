# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import common

from odoo.tools import html2plaintext


@common.tagged('post_install', '-at_install')
class TestSaleMrpInvoices(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_by_lot = cls.env['product.product'].create({
            'name': 'Product By Lot',
            'is_storable': True,
            'tracking': 'lot',
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.lot = cls.env['stock.lot'].create({
            'name': 'LOT0001',
            'product_id': cls.product_by_lot.id,
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
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})

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

        so.picking_ids.button_validate()

        invoice = so._create_invoices()
        invoice.action_post()

        html = self.env['ir.actions.report']._render_qweb_html(
            'account.report_invoice_with_payments', invoice.ids)[0]
        text = html2plaintext(html.decode())
        self.assertRegex(text, r'Product By Lot\n1.00Units\nLOT0001', "There should be a line that specifies 1 x LOT0001")

    def test_report_forecast_for_mto_procure_method(self):
        """
        Check that mto moves are not reported as taking from stock in the forecast report
        """
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        manufacturing_route = self.env.ref('mrp.route_warehouse0_manufacture')
        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'is_storable': True,
            'route_ids': [Command.set((mto_route + manufacturing_route).ids)]
        })

        product.bom_ids = [Command.create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': product.uom_id.id,
            'bom_line_ids': [Command.create({
                'product_id': self.product_by_lot.id,
                'product_qty': 1,
            })]
        })]
        warehouse = self.warehouse
        # make 2 so: so_1 can be fulfilled and so_2 requires a replenishment
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 10.0)
        so_1, so_2 = self.env['sale.order'].create([
            {
                'partner_id': self.partner_a.id,
                'order_line': [Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 8.0,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.list_price,
                })]
            },
            {
                'partner_id': self.partner_a.id,
                'order_line': [Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 7.0,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.list_price,
                })]
            },

        ])
        (so_1 | so_2).action_confirm()
        report_lines = self.env['stock.forecasted_product_product'].with_context(warehouse=warehouse.id).get_report_values(docids=product.ids)['docs']['lines']
        self.assertEqual(len(report_lines), 3)
        so_1_line = report_lines[0]
        self.assertEqual(
            [so_1_line['quantity'], so_1_line['move_out']['id'], so_1_line['replenishment_filled']],
            [8.0, so_1.picking_ids.move_ids.id, True]
        )
        so_2_line = report_lines[1]
        self.assertEqual(
            [so_2_line['quantity'], so_2_line['move_out']['id'], so_2_line['replenishment_filled']],
            [7.0, so_2.picking_ids.move_ids.id, True]
        )
        replenisment_line = report_lines[2]
        self.assertEqual(
            [replenisment_line['document_in'], replenisment_line['document_out'], replenisment_line['quantity'], replenisment_line['move_out'], replenisment_line['replenishment_filled']],
            [False, False, 10.0, None, True]
        )
