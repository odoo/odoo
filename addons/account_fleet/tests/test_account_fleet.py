from freezegun import freeze_time
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form

@tagged('post_install', '-at_install')
class TestAccountFleet(AccountTestInvoicingCommon):

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
        with Form(self.env['account.automatic.entry.wizard'].with_context(context)) as wizard_form:
            wizard_form.action = 'change_period'
            wizard_form.date = '2021-09-15'
            wizard_form.expense_accrual_account = expense_account
            wizard_form.journal_id = bill.journal_id
        wizard = wizard_form.save()

        result_action = wizard.do_action()
        transfer_moves = self.env['account.move'].search(result_action['domain'])
        self.assertEqual(transfer_moves.line_ids.filtered(lambda l: l.account_id == expense_account).vehicle_id, car_1, "Vehicle info is missing")
