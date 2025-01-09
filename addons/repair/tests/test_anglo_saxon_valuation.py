# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAngloSaxonValuation(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.company_id.anglo_saxon_accounting = True

        cls.fifo_product = cls.env['product.product'].create({
            'name': 'product',
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
        })

        cls.basic_accountman = cls.env['res.users'].create({
            'name': 'Basic Accountman',
            'login': 'basic_accountman',
            'password': 'basic_accountman',
            'groups_id': [(6, 0, cls.env.ref('account.group_account_invoice').ids)],
        })

    def _make_in_move(self, product, quantity=1, unit_cost=None):
        unit_cost = unit_cost or product.standard_price
        move = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': quantity,
            'price_unit': unit_cost,
        })
        move._action_confirm()
        move.quantity = quantity
        move.picked = True
        move._action_done()
        return move

    def test_inv_ro_with_auto_fifo_part(self):
        self.fifo_product.standard_price = 100
        self.fifo_product.taxes_id = False

        self._make_in_move(self.fifo_product, unit_cost=10)
        self._make_in_move(self.fifo_product, unit_cost=25)

        ro = self.env['repair.order'].create({
            'product_id': self.product_a.id,
            'partner_id': self.partner_a.id,
            'move_ids': [(0, 0, {
                'repair_line_type': 'add',
                'product_id': self.fifo_product.id,
                'product_uom_qty': 1,
            })],
        })
        ro.action_validate()
        ro.action_repair_start()
        ro.action_repair_end()

        ro.action_create_sale_order()
        so = ro.sale_order_id
        so.action_confirm()
        self.assertEqual(so.order_line.qty_to_invoice, 1)

        invoice = so._create_invoices()
        self.env.invalidate_all()
        self.env.flush_all()
        invoice.with_user(self.basic_accountman).action_post()

        self.assertRecordValues(invoice.line_ids, [
            {'debit': 0, 'credit': 1, 'account_id': self.company_data['default_account_revenue'].id},
            {'debit': 1, 'credit': 0, 'account_id': self.company_data['default_account_receivable'].id},
            {'debit': 0, 'credit': 10, 'account_id': self.company_data['default_account_stock_out'].id},
            {'debit': 10, 'credit': 0, 'account_id': self.company_data['default_account_expense'].id},
        ])
