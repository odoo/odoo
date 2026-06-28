# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.test_account_move_line_tax_details import TestAccountTaxDetailsReport
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountFleet(TestAccountTaxDetailsReport):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref('fleet.fleet_group_manager')
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Audi"})
        model = cls.env["fleet.vehicle.model"].create({"brand_id": brand.id, "name": "A3"})
        cls.car1, cls.car2 = cls.env["fleet.vehicle"].create([
            {"model_id": model.id, "plan_to_change_vehicle": False},
            {"model_id": model.id, "plan_to_change_vehicle": False},
        ])
        cls.expense_account = cls.company_data['default_account_expense']
        cls.asset_account = cls.company_data['default_account_deferred_expense']

    def test_tax_report_with_vehicle_split_repartition(self):
        """Test tax report with split repartition lines across different vehicles."""
        tax = self.env['account.tax'].create({
            'name': 'Split Tax',
            'amount': 10,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': self.expense_account.id}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': self.asset_account.id}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': self.expense_account.id}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50, 'account_id': self.asset_account.id}),
            ],
        })

        bill = self.init_invoice('in_invoice', invoice_date='2025-10-16', post=False)
        bill.write({
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'account_id': self.expense_account.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax.ids)],
                    'vehicle_id': self.car1.id
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'account_id': self.expense_account.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax.ids)],
                    'vehicle_id': self.car2.id
                }),
            ]
        })
        bill.action_post()

        tax_details = self._get_tax_details()
        # 2 base lines x 2 split repartition lines (50% expense + 50% asset) = 4 tax details
        self.assertEqual(len(tax_details), 4)
        for line in tax_details:
            self.assertEqual(line['tax_amount'], 5)

    def test_tax_report_with_mixed_vehicle_lines(self):
        """Test tax report with mixed vehicle/non-vehicle base lines sharing a tax.

        When the tax repartition line uses a non-expense account (use_in_tax_closing=True),
        vehicle_id is excluded from the tax line grouping key, causing a single merged
        tax line with vehicle_id = NULL. The vehicle_id matching must allow this tax line
        to match both base lines to avoid tax report inconsistencies.
        """
        tax = self.env['account.tax'].create({
            'name': 'Test Tax 10%',
            'amount': 10,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100, 'account_id': self.asset_account.id}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100, 'account_id': self.asset_account.id}),
            ],
        })

        bill = self.init_invoice('in_invoice', invoice_date='2025-10-16', post=False)
        bill.write({
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'account_id': self.expense_account.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax.ids)],
                    'vehicle_id': self.car1.id,
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'account_id': self.expense_account.id,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ]
        })
        bill.action_post()

        tax_details = self._get_tax_details()
        self.assertEqual(len(tax_details), 2)
        for line in tax_details:
            self.assertEqual(line['tax_amount'], 10)
