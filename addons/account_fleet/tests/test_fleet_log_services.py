# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestFleetLogServices(AccountTestInvoicingCommon, common.TransactionCase):

    def test_fleet_log_services_amount(self):
        brand = self.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = self.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        car = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "plan_to_change_car": False
        })

        partner = self.env['res.partner'].create({
            "name": "Test Partner",
        })

        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'currency_id': self.env.ref('base.EUR').id,
            'line_ids': [
                (0, 0, {
                    'currency_id': self.currency_data['currency'].id,
                    'account_id': self.company_data['default_account_expense'].id,
                    'vehicle_id': car.id,
                    'quantity': 1,
                    'price_unit': 5000
                })
            ],
        })
        move.action_post()
        line = move.line_ids[0]
        fleet_service = self.env['fleet.vehicle.log.services'].search([('vendor_id', '=', partner.id),
                                                                       ('description', '=', False)])

        self.assertNotEqual(line.debit, line.price_subtotal)
        self.assertEqual(fleet_service.amount, line.debit)
