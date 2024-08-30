# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields


class ValuationReconciliationTestCommon(AccountTestInvoicingCommon):
    """ Base class for tests checking interim accounts reconciliation works
    in anglosaxon accounting. It sets up everything we need in the tests, and is
    extended in both sale_stock and purchase modules to run the 'true' tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.groups_id += cls.env.ref('stock_account.group_stock_accounting_automatic')

        cls.stock_account_product_categ = cls.env['product.category'].create({
            'name': 'Test category',
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
            'property_stock_valuation_account_id': cls.company_data['default_account_stock_valuation'].id,
            'property_stock_account_input_categ_id': cls.company_data['default_account_stock_in'].id,
            'property_stock_account_output_categ_id': cls.company_data['default_account_stock_out'].id,
        })

        uom_unit = cls.env.ref('uom.product_uom_unit')

        cls.test_product_order = cls.env['product.product'].create({
            'name': "Test product template invoiced on order",
            'standard_price': 42.0,
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })
        cls.test_product_delivery = cls.env['product.product'].create({
            'name': 'Test product template invoiced on delivery',
            'standard_price': 42.0,
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

        cls.res_users_stock_user = cls.env['res.users'].create({
            'name': "Inventory User",
            'login': "su",
            'email': "stockuser@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('stock.group_stock_user').id])],
            })

    @classmethod
    def collect_company_accounting_data(cls, company):
        company_data = super().collect_company_accounting_data(company)

        # Create stock config.
        company_data.update({
            'default_account_stock_in': cls.env['account.account'].with_company(company).create({
                'name': 'default_account_stock_in',
                'code': 'STOCKIN',
                'reconcile': True,
                'account_type': 'asset_current',
            }),
            'default_account_stock_out': cls.env['account.account'].with_company(company).create({
                'name': 'default_account_stock_out',
                'code': 'STOCKOUT',
                'reconcile': True,
                'account_type': 'asset_current',
            }),
            'default_account_stock_valuation': cls.env['account.account'].with_company(company).create({
                'name': 'default_account_stock_valuation',
                'code': 'STOCKVAL',
                'reconcile': True,
                'account_type': 'asset_current',
            }),
            'default_warehouse': cls.env['stock.warehouse'].search(
                [('company_id', '=', company.id)],
                limit=1,
            ),
        })
        return company_data

    def check_reconciliation(self, invoice, picking, full_reconcile=True, operation='purchase'):
        interim_account_id = self.company_data['default_account_stock_in'].id if operation == 'purchase' else self.company_data['default_account_stock_out'].id
        invoice_line = invoice.line_ids.filtered(lambda line: line.account_id.id == interim_account_id)

        stock_moves = picking.move_ids

        valuation_line = stock_moves.account_move_ids.line_ids.filtered(lambda x: x.account_id.id == interim_account_id)

        if invoice.is_purchase_document() and any(l.display_type == 'cogs' for l in invoice_line):
            self.assertEqual(len(invoice_line), 2, "Only two line2 should have been written by invoice in stock input account")
            self.assertTrue(all(vl.reconciled for vl in valuation_line) or invoice_line[0].reconciled or invoice_line[1].reconciled, "The valuation and invoice line should have been reconciled together.")
        else:
            self.assertEqual(len(invoice_line), 1, "Only one line should have been written by invoice in stock input account")
            self.assertTrue(all(vl.reconciled for vl in valuation_line) or invoice_line.reconciled, "The valuation and invoice line should have been reconciled together.")

        if invoice.move_type not in ('out_refund', 'in_refund'):
            # self.assertEqual(len(valuation_line), 1, "Only one line should have been written for stock valuation in stock input account")

            if full_reconcile:
                self.assertTrue(all(vl.full_reconcile_id for vl in valuation_line), "The reconciliation should be total at that point.")
            else:
                self.assertFalse(all(vl.full_reconcile_id for vl in valuation_line), "The reconciliation should not be total at that point.")

    def _process_pickings(self, pickings, date=False, quantity=False):

        def do_picking():
            pickings.action_confirm()
            pickings.action_assign()
            if quantity:
                for picking in pickings:
                    for ml in picking.move_line_ids:
                        ml.quantity = quantity
            pickings.move_ids.picked = True
            pickings._action_done()

        if not date:
            date = fields.Date.today()
            do_picking()
            return
        with freeze_time(date):
            do_picking()
