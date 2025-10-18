# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo import Command
from odoo.addons.account.tests.test_account_move_line_tax_details import TestAccountTaxDetailsReport
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountFleet(TestAccountTaxDetailsReport):

    @freeze_time('2021-09-15')
    def test_transfer_wizard_vehicle_info_propagation(self):
        brand = self.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = self.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        car_1 = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "plan_to_change_car": False
        })

        bill = self.init_invoice('in_invoice', products=self.product_a, invoice_date='2021-09-01', post=False)
        bill.invoice_line_ids.write({'vehicle_id': car_1.id})
        bill.action_post()

        context = {'active_model': 'account.move.line', 'active_ids': bill.invoice_line_ids.ids}
        expense_account = self.company_data['default_account_expense']
        wizard = self.env['account.automatic.entry.wizard'].with_context(context).create({
            'action': 'change_period',
            'date': '2021-09-10',
            'percentage': 60,
            'journal_id': self.company_data['default_journal_misc'].id,
            'expense_accrual_account': expense_account.id,
            'revenue_accrual_account': self.env['account.account'].create({
                'name': 'Accrual Revenue Account',
                'code': '765432',
                'account_type': 'expense',
                'reconcile': True,
            }).id,
        })
        result_action = wizard.do_action()
        transfer_moves = self.env['account.move'].search(result_action['domain'])
        self.assertEqual(transfer_moves.line_ids.filtered(lambda l: l.account_id == expense_account).vehicle_id, car_1, "Vehicle info is missing")

    def test_tax_report_with_vehicle_split_repartition(self):
        """Test tax report with split repartition lines across different vehicles."""
        ChartTemplate = self.env['account.chart.template']
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "Audi"})
        model = self.env["fleet.vehicle.model"].create({"brand_id": brand.id, "name": "A3"})
        cars = self.env["fleet.vehicle"].create([
            {"model_id": model.id, "plan_to_change_car": False},
            {"model_id": model.id, "plan_to_change_car": False},
        ])

        expense_account = ChartTemplate.ref('expense')
        asset_account = ChartTemplate.ref('current_assets')

        tax = self.env['account.tax'].create({
            'name': 'Split Tax',
            'amount': 10,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': expense_account.id}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': asset_account.id}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': expense_account.id}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': asset_account.id}),
            ],
        })

        bill = self.init_invoice('in_invoice', invoice_date='2025-10-16', post=False)
        bill.write({
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'account_id': expense_account.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax.ids)],
                    'vehicle_id': cars[0].id
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'account_id': expense_account.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax.ids)],
                    'vehicle_id': cars[1].id
                }),
            ]
        })
        bill.action_post()

        tax_details = self._get_tax_details()
        self.assertEqual(len(tax_details), 2)
        for line in tax_details:
            self.assertEqual(line['tax_amount'], 5)
