# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestAccountBudgetCommon
from odoo import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPurchaseOrder(TestAccountBudgetCommon):

    def test_access_purchase_order(self):
        """ Make sure a purchase manager can access a purchase order linked to a budget. """

        self.budget_analytic_expense.action_budget_confirm()
        purchase_partner = self.env['res.partner'].create({'name': 'Purchaser'})
        purchase_user = self.env['res.users'].create({
            'login': 'Purchaser',
            'partner_id': purchase_partner.id,
            'groups_id': [Command.set(self.env.ref('purchase.group_purchase_manager').ids)],
        })

        self.assertFalse(
            self.purchase_order.with_user(purchase_user).order_line.budget_line_ids,
            " Purchase Order should be accessible by purchase manager even without accounting rights. "
        )

    def test_purchase_order_is_above_budget(self):
        """ Test that is_above_budget field is computed correctly """
        # budget amount of 10000.0 for "analytic_account_partner_b" and "analytic_account_administratif"
        self.budget_analytic_expense.action_budget_confirm()
        # PO that is not above budget
        po_1 = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                # the first line should be ignored as one of the analytic account is missing
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'product_qty': 100,
                    'analytic_distribution': {self.analytic_account_administratif.id: 100},
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 1000.0,
                    'product_qty': 1,
                    'analytic_distribution': {"%s,%s" % (self.analytic_account_partner_b.id, self.analytic_account_administratif.id): 100},
                }),
            ]
        })
        self.assertFalse(po_1.is_above_budget)
        self.assertFalse(po_1.order_line[0].is_above_budget)
        self.assertFalse(po_1.order_line[1].is_above_budget)
        # PO that is above budget
        po_2 = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'product_qty': 100,
                    'analytic_distribution': {"%s,%s" % (self.analytic_account_partner_b.id, self.analytic_account_administratif.id): 100},
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 1000.0,
                    'product_qty': 1,
                    'analytic_distribution': {"%s,%s" % (self.analytic_account_partner_b.id, self.analytic_account_administratif.id): 100},
                }),
            ]
        })
        self.assertTrue(po_2.is_above_budget)
        self.assertTrue(po_2.order_line[0].is_above_budget)
        self.assertFalse(po_2.order_line[1].is_above_budget)
