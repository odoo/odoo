# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged('post_install', '-at_install')
class TestAngloSaxonValuation(TestStockValuationCommon):

    def test_inv_ro_with_auto_fifo_part(self):
        self.company.anglo_saxon_accounting = True
        self.product_fifo_auto.standard_price = 100
        self.product_fifo_auto.taxes_id = False

        self._make_in_move(self.product_fifo_auto, 1, unit_cost=10)
        self._make_in_move(self.product_fifo_auto, 1, unit_cost=25)

        basic_accountman = self._create_new_internal_user(
            name='Basic Accountman',
            login='basic_accountman',
            groups='account.group_account_invoice',
        )

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
        ro.action_repair_start()
        ro.action_repair_end()

        ro.sudo().action_create_sale_order()
        so = ro.sale_order_id
        so.sudo().action_confirm()
        self.assertEqual(so.order_line.qty_to_invoice, 1)

        invoice = so._create_invoices()
        self.env.invalidate_all()
        self.env.flush_all()
        invoice.with_user(basic_accountman).action_post()

        self.assertRecordValues(invoice.line_ids, [
            {'debit': 0, 'credit': 20, 'account_id': self.account_income.id},
            {'debit': 20, 'credit': 0, 'account_id': self.account_receivable.id},
            {'debit': 0, 'credit': 10, 'account_id': self.account_stock_valuation.id},
            {'debit': 10, 'credit': 0, 'account_id': self.account_expense.id},
        ])

    def test_ro_invoice_double_valuation(self):
        """This test make sure that the valuation entry for a repair is created only once.
           It could happen if the repair order was already creating the valuation, then the sale order would also create it
           when invoiced"""

        self.product_fifo_auto.taxes_id = False
        self.env['stock.quant']._update_available_quantity(self.product_fifo_auto, self.warehouse.lot_stock_id, 5)

        self.account_inventory = self.env['account.account'].create({
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
        ro.action_repair_start()
        ro.action_repair_end()

        ro.sudo().action_create_sale_order()
        so = ro.sale_order_id
        so.sudo().action_confirm()
        self.assertEqual(so.order_line.qty_to_invoice, 1)

        invoice = so._create_invoices()
        invoice.action_post()

        self.assertRecordValues(invoice.line_ids, [
            {'debit': 0.0, 'credit': 20.0, 'account_id': self.account_income.id},
            {'debit': 20.0, 'credit': 0.0, 'account_id': self.account_receivable.id},
        ])
        self.assertRecordValues(ro.move_ids.account_move_id.line_ids, [
            {'debit': 0.0, 'credit': 10.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 10.0, 'credit': 0.0, 'account_id': self.account_inventory.id},
        ])
