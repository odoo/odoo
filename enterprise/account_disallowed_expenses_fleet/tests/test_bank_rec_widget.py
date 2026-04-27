# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon


@tagged('post_install', '-at_install')
class TestBankRecWidgetFleet(TestBankRecWidgetCommon):
    def test_bank_rec_vehicle(self):
        vehicle_exp_acc, other_exp_acc, tax_acc = self.env['account.account'].create([{
            'code': code,
            'name': name,
        } for code, name in [
            ('611010', 'Vehicle Expenses'),
            ('611020', 'Other Expenses'),
            ('811000', 'Tax Account'),
        ]])
        self.env['account.disallowed.expenses.category'].create({
            'code': '23456',
            'name': 'Robins DNA',
            'car_category': True,
            'account_ids': [Command.set(vehicle_exp_acc.ids)],
        })
        fleet_brand = self.env['fleet.vehicle.model.brand'].create({
            'name': 'Odoo',
        })
        fleet_model = self.env['fleet.vehicle.model'].create({
            'name': 'v16',
            'brand_id': fleet_brand.id,
            'vehicle_type': 'car',
        })
        robinmobile = self.env['fleet.vehicle'].create({
            'model_id': fleet_model.id,
            'license_plate': 'BE1234-2'
        })
        regular_tax = self.env['account.tax'].create({
            'name': 'Regular',
            'amount_type': 'percent',
            'amount': 25.0,
            'type_tax_use': 'sale',
            'company_id': self.company_data['company'].id,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'account_id': tax_acc.id, 'use_in_tax_closing': True}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'account_id': tax_acc.id, 'use_in_tax_closing': True}),
            ],
        })
        car_tax = self.env['account.tax'].create({
            'name': 'Car',
            'amount_type': 'percent',
            'amount': 25.0,
            'type_tax_use': 'sale',
            'company_id': self.company_data['company'].id,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'factor_percent': 50}),
                Command.create({'factor_percent': 50, 'account_id': tax_acc.id, 'use_in_tax_closing': True}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'factor_percent': 50}),
                Command.create({'factor_percent': 50, 'account_id': tax_acc.id, 'use_in_tax_closing': True}),
            ],
        })
        st_line = self._create_st_line(1000.0, partner_id=None, partner_name="The Driver")

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        line = wizard.line_ids.filtered(lambda x: x.flag == 'auto_balance')
        wizard._js_action_mount_line_in_edit(line.index)

        line.account_id = other_exp_acc
        wizard._line_value_changed_account_id(line)
        self.assertRecordValues(line, [{
            'account_id': other_exp_acc.id,
            'vehicle_required': False,
        }])

        line.account_id = vehicle_exp_acc
        wizard._line_value_changed_account_id(line)
        self.assertRecordValues(line, [{
            'account_id': vehicle_exp_acc.id,
            'vehicle_required': True,
        }])

        line.vehicle_id = robinmobile
        line.tax_ids = [Command.set(regular_tax.ids)]
        wizard._line_value_changed_vehicle_id(line)
        tax_lines = wizard.line_ids.filtered(lambda x: x.flag == 'tax_line')
        self.assertRecordValues(tax_lines, [{
            'account_id': tax_acc.id,
            'vehicle_id': False,
        }])

        line.tax_ids = [Command.set(car_tax.ids)]
        wizard._line_value_changed_tax_ids(line)
        tax_lines = wizard.line_ids.filtered(lambda x: x.flag == 'tax_line')
        self.assertRecordValues(tax_lines, [
            # pylint: disable=C0326
            { 'account_id': vehicle_exp_acc.id, 'vehicle_id': robinmobile.id},
            { 'account_id': tax_acc.id,         'vehicle_id': False },
        ])
