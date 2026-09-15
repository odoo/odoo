# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged('post_install', '-at_install')
class TestAngloSaxonValuation(TestStockValuationCommon):

    _test_user_groups = (
        'product.group_product_manager',  # product cost/category writes
        'stock.group_stock_manager',  # subject: repair orders & deliveries
        'account.group_account_invoice',  # anglo-saxon COGS entries asserted
    )

    _test_user_name = 'Test Stock & Account User'

    def test_ro_invoice_double_valuation(self):
        """This test make sure that the valuation entry for a repair is created only once.
           It could happen if the repair order was already creating the valuation, then the sale order would also create it
           when invoiced"""

        self.product_fifo_auto.taxes_id = False
        self.env['stock.quant'].create({
            'product_id': self.product_fifo_auto.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'inventory_quantity': 5,
        }).action_apply_inventory()

        self.account_inventory = self.env['account.account'].sudo().create({
            'name': 'Inventory Account',
            'code': '100101',
            'account_type': 'asset_current',
        })
        inventory_locations = self.warehouse.repair_type_id.default_location_dest_id
        inventory_locations.valuation_account_id = self.account_inventory.id

        ro = self.env['repair.order'].create({
            'product_id': self.product.id,
            'partner_id': self.owner.id,
            'move_ids': [(0, 0, {
                'repair_line_type': 'add',
                'product_id': self.product_fifo_auto.id,
                'product_uom_qty': 1,
            })],
        })
        ro.action_validate()
        ro.action_repair_end()

        ro.sudo().action_create_sale_order()
        so = ro.sale_order_id
        so.sudo().action_confirm()
        self.assertEqual(so.order_line.qty_to_invoice, 1)

        invoice = so._create_invoices()
        invoice.action_post()
        self.assertRecordValues(invoice.line_ids.sorted('account_id'), [
            {'debit': 0.0, 'credit': 10.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 20.0, 'credit': 0.0, 'account_id': self.account_receivable.id},
            {'debit': 0.0, 'credit': 20.0, 'account_id': self.account_income.id},
            {'debit': 10.0, 'credit': 0.0, 'account_id': self.account_expense.id},
        ])
        self.assertRecordValues(ro.move_ids.account_move_id.line_ids, [
            {'debit': 0.0, 'credit': 10.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 10.0, 'credit': 0.0, 'account_id': self.account_inventory.id},
        ])
