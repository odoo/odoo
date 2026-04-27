from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import Command, fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveFleet(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.batmobile = cls.env['fleet.vehicle'].create({
            'model_id': cls.env['fleet.vehicle.model'].create({
                'name': 'Batmobile',
                'brand_id': cls.env['fleet.vehicle.model.brand'].create({
                    'name': 'Wayne Enterprises',
                }).id,
                'vehicle_type': 'car',
                'default_fuel_type': 'hydrogen',
            }).id,
            'rate_ids': [Command.create({
                'date_from': fields.Date.from_string('2022-01-01'),
                'rate': 31.0,
            })],
        })

    def test_account_move_line_vehicle_id(self):
        self.company_data['default_tax_purchase'].invoice_repartition_line_ids.use_in_tax_closing = False

        # Create bill with vehicle id on invoice line and tax, will create a tax line with the same vehicle id
        bill = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'date': fields.Date.from_string('2022-01-15'),
            'invoice_date': fields.Date.from_string('2022-01-15'),
            'invoice_line_ids': [
                Command.create({
                    'name': 'test_line',
                    'account_id': self.company_data['default_account_expense'].id,
                    'quantity': 1,
                    'price_unit': 100.0,
                    'vehicle_id': self.batmobile.id,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                }),
            ]
        }])

        # Check vehicle id is set on product and tax line
        self.assertFalse(bill.line_ids.filtered(lambda l: l.display_type in ('product', 'tax') and not l.vehicle_id))

        # Remove vehicle id from invoice line, should remove also from the tax line
        bill.invoice_line_ids.write({'vehicle_id': False})
        self.assertRecordValues(bill.line_ids.sorted('balance'), [
            {
                'balance': -115.0,
                'tax_base_amount': 0.0,
                'tax_ids': [],
                'vehicle_id': False,
            }, {
                'balance': 15.0,
                'tax_base_amount': 100.0,
                'tax_ids': [],
                'vehicle_id': False,
            }, {
                'balance': 100,
                'tax_base_amount': 0,
                'vehicle_id': False,
                'tax_ids': self.company_data['default_tax_purchase'].ids,
            },
        ])
