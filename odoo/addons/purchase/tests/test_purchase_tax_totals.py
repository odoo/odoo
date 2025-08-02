# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.account.tests.test_invoice_tax_totals import TestTaxTotals
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class PurchaseTestTaxTotals(TestTaxTotals):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.po_product = cls.env['product.product'].create({
            'name': 'Odoo course',
            'type': 'service',
        })

    def _create_document_for_tax_totals_test(self, lines_data):
        # Overridden in order to run the inherited tests with purchase.order's
        # tax_totals field instead of account.move's

        lines_vals = [
            (0, 0, {
                'name': 'test',
                'product_id': self.po_product.id,
                'product_qty': 1,
                'product_uom': self.po_product.uom_po_id.id,
                'price_unit': amount,
                'taxes_id': [(6, 0, taxes.ids)],
            })
        for amount, taxes in lines_data]

        return self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': lines_vals,
        })

    def test_tax_is_used_when_in_transactions(self):
        ''' Ensures that a tax is set to used when it is part of some transactions '''

        # Account.move is one type of transaction
        tax_purchase = self.env['account.tax'].create({
            'name': 'test_is_used_purchase',
            'amount': '100',
        })

        self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': 'order_line',
                    'product_id': self.po_product.id,
                    'product_qty': 1.0,
                    'price_unit': 100.0,
                    'taxes_id': [Command.set(tax_purchase.ids)],
                }),
            ],
        })
        tax_purchase.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_purchase.is_used)

    def test_archived_tax_totals(self):
        tax_10 = self.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
            'tax_group_id': self.tax_group1.id,
        })

        po = self._create_document_for_tax_totals_test([
            (100.0, tax_10),
        ])
        po.button_confirm()
        po.order_line.qty_received = 1
        po.action_create_invoice()

        invoice = po.invoice_ids
        invoice.invoice_date = '2020-01-01'
        invoice.action_post()

        old_ammount = po.amount_total
        tax_10.active = False
        self.assertEqual(po.amount_total, old_ammount)
