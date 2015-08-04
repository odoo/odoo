# -*- coding: utf-8 -*-

from openerp import tools
from openerp.tests import common
from openerp.modules.module import get_module_resource


class TestDeferredRevenue(common.TransactionCase):

    def _load(self, module, *args):
        tools.convert_file(self.cr, 'account_deferred_revenue',
                           get_module_resource(module, *args),
                           {}, 'init', False, 'test', self.registry._assertion_report)

    def test_00_account_asset_asset(self):
        self._load('account', 'test', 'account_minimal_test.xml')
        self._load('account_deferred_revenue', 'test', 'account_deferred_revenue_demo_test.xml')

        invoice = self.env['account.invoice'].create({
            'partner_id': self.ref("base.res_partner_12"),
            'account_id': self.ref("account_deferred_revenue.a_sale"),
        })
        self.env['account.invoice.line'].create({
            'invoice_id': invoice.id,
            'account_id': self.ref("account_deferred_revenue.a_sale"),
            'name': 'Insurance claim',
            'price_unit': 450,
            'quantity': 1,
            'asset_category_id': self.ref("account_deferred_revenue.account_asset_category_sale1"),
        })
        invoice.signal_workflow('invoice_open')

        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        line_obj = self.env['account.asset.depreciation.line']
        recognition_ids = self.env['account.asset.asset'].search([('code', '=', invoice.number)])
        self.assertTrue(recognition_ids,
            'Revenue recognition has been not created from invoice.')

        # I confirm revenue recognition.
        for asset in recognition_ids:
            asset.validate()
        recognition = recognition_ids[0]
        first_invoice_line = invoice.invoice_line_ids[0]
        self.assertTrue(recognition.state == 'open',
            'Recognition should be in Open state')
        self.assertEqual(recognition.value, first_invoice_line.price_subtotal,
            'Recognition value is not same as invoice line.')

        # I post installment lines.
        line_ids = [rec for rec in recognition.depreciation_line_ids]
        for line in line_ids:
            line.create_move()

        # I check that move line is created from posted installment lines.
        self.assertEqual(len(recognition.depreciation_line_ids), len(recognition.account_move_ids),
            'Move lines not created correctly.')

        # I check data in move line and installment line.
        first_installment_line = recognition.depreciation_line_ids[0]
        first_move = recognition.account_move_ids[0]
        self.assertEqual(first_installment_line.amount, first_move.amount,
            'First installment line amount is incorrect.')
        remaining_value = recognition.value - first_installment_line.amount
        self.assertEqual(first_installment_line.remaining_value, recognition.value - first_installment_line.amount,
            'Remaining value is incorrect.')

        # I check next installment date.
        last_installment_date = datetime.strptime(first_installment_line.depreciation_date, '%Y-%m-%d')
        installment_date = (last_installment_date+relativedelta(months=+recognition.method_period))
        self.assertEqual(recognition.depreciation_line_ids[1].depreciation_date, str(installment_date.date()),
            'Installment date is incorrect.')
