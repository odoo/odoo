# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountFleet(AccountTestInvoicingCommon):

    @freeze_time('2021-09-15')
    def test_transfer_wizard_vehicle_info_propagation(self):
        self.env.user.group_ids |= self.env.ref("fleet.fleet_group_manager")
        brand = self.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = self.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        car_1 = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "plan_to_change_car": False,
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
