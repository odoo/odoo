# coding: utf-8
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

import base64
from freezegun import freeze_time

@tagged('post_install_l10n', "post_install", "-at_install")
class Test1099(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.company.write({
            "street": "1 W Seneca St",
            "street2": "Floor 26",
            "city": "Buffalo",
            "state_id": cls.env["res.country.state"].search([("name", "=", "New York")], limit=1).id,
            "zip": "14203",
            "country_id": cls.env.ref("base.us").id,
            "phone": "(716) 249-2880",
            "vat": "987654321",
        })

        cls.vendor_non_1099 = cls.env["res.partner"].create({
            "name": "non-1099 vendor",
        })

        cls.vendor_1099 = cls.env["res.partner"].create({
            "name": "1099 vendor",
            "street": "250 Executive Park Blvd",
            "street2": "#3400",
            "city": "San Francisco",
            "state_id": cls.env["res.country.state"].search([("name", "=", "California")], limit=1).id,
            "zip": "94134",
            "country_id": cls.env.ref("base.us").id,
            "phone": "(650) 691-3277",
            "vat": "123456789",
            "email": "vendor@example.com",
            "box_1099_id": cls.env.ref("l10n_us_1099.box_1099_misc_03").id,
        })

        cls.liquidity_account = cls.env["account.account"].search(
            [("account_type", "=", "asset_cash")],
            limit=1
        )
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense")],
            limit=1
        )

        company_2_id = cls.company_data_2["company"].id
        cls.liquidity_account_comp2 = cls.env["account.account"].search(
            [
                ("company_id", "=", company_2_id),
                ("account_type", "=", "asset_cash"),
            ],
            limit=1
        )
        cls.expense_account_comp2 = cls.env["account.account"].search(
            [
                ("company_id", "=", company_2_id),
                ("account_type", "=", "expense")
            ],
            limit=1
        )

    @freeze_time("2021-02-10")
    def test1099Wizard(self):
        move_vals = {
            "date": "2020-06-06",  # wizard includes last year by default
            "line_ids": [
                (0, 0, {
                    "name": "debit",
                    "partner_id": self.vendor_non_1099.id,
                    "account_id": self.expense_account.id,
                    "debit": 100.0,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "name": "credit",
                    "partner_id": self.vendor_non_1099.id,
                    "account_id": self.liquidity_account.id,
                    "debit": 0.0,
                    "credit": 100.0,
                }),
            ],
        }
        move = self.env["account.move"].create(move_vals)
        move.action_post()

        # these should not be included when the user is in company 1
        move_vals_company_2 = {
            "date": "2020-06-06",  # wizard includes last year by default
            "line_ids": [
                (0, 0, {
                    "name": "debit",
                    "partner_id": self.vendor_1099.id,
                    "account_id": self.expense_account_comp2.id,
                    "debit": 200.0,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "name": "credit",
                    "partner_id": self.vendor_1099.id,
                    "account_id": self.liquidity_account_comp2.id,
                    "debit": 0.0,
                    "credit": 200.0,
                }),
            ],
        }
        self.env["account.move"].with_company(self.company_data_2["company"]).create(move_vals_company_2).action_post()

        move_vals["line_ids"][0][2]["partner_id"] = self.vendor_1099.id
        move_vals["line_ids"][1][2]["partner_id"] = self.vendor_1099.id
        move = self.env["account.move"].create(move_vals)
        move.action_post()
        expected_lines = move.line_ids.filtered("credit")

        move_vals["line_ids"][0][2]["debit"] = 150
        move_vals["line_ids"][1][2]["credit"] = 150
        move = self.env["account.move"].create(move_vals)
        move.action_post()
        expected_lines |= move.line_ids.filtered("credit")

        # switch to company 1
        self.env.user.company_ids = self.env.company

        wizard = self.env["l10n_us_1099.wizard"].create({})
        self.assertEqual(wizard.lines_to_export, expected_lines, "Wizard should contain the credit part of the 1099 vendor entry.")

        wizard.action_generate()
        csv_content = base64.b64decode(wizard.generated_csv_file).decode().splitlines()

        self.maxDiff = None  # show the full diff in case of errors
        header = (
            "Payer Name,Payer Address Line 1,Payer Address Line 2,Payer City,Payer State,Payer Zip,Payer Country,Payer Phone Number,Payer TIN,"
            "Payee Name,Payee Address Line 1,Payee Address Line 2,Payee City,Payee State,Payee Zip,Payee Country,Payee Email,Payee TIN,NEC - 1 Nonemployee compensation,"
            "MISC - 1 Rents,MISC - 2 Royalties,MISC - 3 Other income,MISC - 5 Fishing boat proceeds,MISC - 6 Medical and health care payments,"
            "MISC - 8 Substitute payments in lieu of dividends or interest,MISC - 9 Crop insurance proceeds,MISC - 10 Gross proceeds paid to an attorney,"
            "MISC - 11 Fish purchased for resale,MISC - 12 Section 409A deferrals,MISC - 13 Excess golden parachute payments,MISC - 14 Nonqualified deferred compensation"
        )
        self.assertEqual(csv_content[0], header, "Wizard did not generate the expected header.")

        expected_line = (
            "company_1_data,1 W Seneca St,Floor 26,Buffalo,New York,14203,United States,(716) 249-2880,987654321,1099 vendor,250 Executive Park Blvd,"
            "#3400,San Francisco,California,94134,United States,vendor@example.com,123456789,0,0,0,250.0,0,0,0,0,0,0,0,0,0"
        )
        self.assertEqual(csv_content[1], expected_line, "Wizard did not generate the expected line for the 1099 vendor.")
        self.assertEqual(len(csv_content), 2, "Wizard should exactly generate the two lines above.")

    @freeze_time("2021-02-10")
    def test_1099_wizard_manual_export_lines(self):
        """ Test that lines added manually are computed correctly for 2 vendors """
        vendor_x = self.env['res.partner'].create({
            'name': 'Vendor X',
            'street': '123 Test street',
            'street2': '#6666',
            'city': 'Brooklyn',
            'state_id': self.env.ref('base.state_us_27').id,
            'zip': '11202',
            'country_id': self.env.ref('base.us').id,
            'vat': '192837465',
            'email': 'vendor_x@example.com',
            'box_1099_id': self.env.ref('l10n_us_1099.box_1099_misc_03').id,
        })
        # create a first move for "1099 vendor"
        move_1 = self.env['account.move'].create({
            'date': '2020-06-06',
            'line_ids': [
                Command.create({
                    'name': 'debit',
                    'partner_id': self.vendor_1099.id,
                    'account_id': self.expense_account.id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'name': 'credit',
                    'partner_id': self.vendor_1099.id,
                    'account_id': self.liquidity_account.id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
        })
        move_1.action_post()
        # create a first move for "Vendor X"
        move_2 = self.env['account.move'].create({
            'date': '2020-06-07',
            'line_ids': [
                Command.create({
                    'name': 'debit',
                    'partner_id': vendor_x.id,
                    'account_id': self.expense_account.id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'name': 'credit',
                    'partner_id': vendor_x.id,
                    'account_id': self.liquidity_account.id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ],
        })
        move_2.action_post()
        # create a second move for "1099 vendor"
        move_3 = self.env['account.move'].create({
            'date': '2020-06-08',
            'line_ids': [
                Command.create({
                    'name': 'debit',
                    'partner_id': self.vendor_1099.id,
                    'account_id': self.expense_account.id,
                    'debit': 150.0,
                    'credit': 0.0,
                }),
                Command.create({
                    'name': 'credit',
                    'partner_id': self.vendor_1099.id,
                    'account_id': self.liquidity_account.id,
                    'debit': 0.0,
                    'credit': 150.0,
                }),
            ],
        })
        move_3.action_post()

        lines_to_export = (move_1 + move_2 + move_3).line_ids.filtered('credit')
        wizard = self.env['l10n_us_1099.wizard'].create({'lines_to_export': lines_to_export})
        wizard.action_generate()
        csv_content = base64.b64decode(wizard.generated_csv_file).decode().splitlines()

        self.maxDiff = None  # show the full diff in case of errors
        header = (
            'Payer Name,Payer Address Line 1,Payer Address Line 2,Payer City,Payer State,Payer Zip,Payer Country,Payer Phone Number,Payer TIN,'
            'Payee Name,Payee Address Line 1,Payee Address Line 2,Payee City,Payee State,Payee Zip,Payee Country,Payee Email,Payee TIN,NEC - 1 Nonemployee compensation,'
            'MISC - 1 Rents,MISC - 2 Royalties,MISC - 3 Other income,MISC - 5 Fishing boat proceeds,MISC - 6 Medical and health care payments,'
            'MISC - 8 Substitute payments in lieu of dividends or interest,MISC - 9 Crop insurance proceeds,MISC - 10 Gross proceeds paid to an attorney,'
            'MISC - 11 Fish purchased for resale,MISC - 12 Section 409A deferrals,MISC - 13 Excess golden parachute payments,MISC - 14 Nonqualified deferred compensation'
        )
        self.assertEqual(csv_content[0], header, 'Wizard did not generate the expected header.')

        expected_lines = [(
            'company_1_data,1 W Seneca St,Floor 26,Buffalo,New York,14203,United States,(716) 249-2880,987654321,1099 vendor,250 Executive Park Blvd,'
            '#3400,San Francisco,California,94134,United States,vendor@example.com,123456789,0,0,0,250.0,0,0,0,0,0,0,0,0,0'
        ), (
            'company_1_data,1 W Seneca St,Floor 26,Buffalo,New York,14203,United States,(716) 249-2880,987654321,Vendor X,123 Test street,'
            '#6666,Brooklyn,New York,11202,United States,vendor_x@example.com,192837465,0,0,0,100.0,0,0,0,0,0,0,0,0,0'
        )]
        self.assertEqual(csv_content[1], expected_lines[0], 'Wizard did not generate the expected line for 1099 vendor.')
        self.assertEqual(csv_content[2], expected_lines[1], 'Wizard did not generate the expected line for Vendor X.')
        self.assertEqual(len(csv_content), 3, 'Wizard should exactly generate the three lines above.')
