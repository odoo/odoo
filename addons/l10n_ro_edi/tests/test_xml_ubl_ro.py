from odoo import Command
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLRO(TestUBLCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="ro"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.ro').id,
            'state_id': cls.env.ref('base.RO_B').id,
            'name': 'Hudson Construction',
            'city': 'SECTOR1',
            'zip': '010101',
            'vat': 'RO1234567897',
            'phone': '+40 123 456 789',
            'street': "Strada Kunst, 3",
            'invoice_is_ubl_cii': True,
        })

        cls.currency_data['currency'] = cls.env.ref('base.RON')

        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'RO98RNCB1234567890123456',
        })

        cls.partner_a = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.ro').id,
            'state_id': cls.env.ref('base.RO_B').id,
            'name': 'Roasted Romanian Roller',
            'city': 'SECTOR3',
            'zip': '010101',
            'vat': 'RO1234567897',
            'phone': '+40 123 456 780',
            'street': "Rolling Roast, 88",
            'bank_ids': [(0, 0, {'acc_number': 'RO98RNCB1234567890123456'})],
            'ref': 'ref_partner_a',
        })

        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.ro').id,
        })

    ####################################################
    # Test export - import
    ####################################################

    def create_move(self, move_type, send=True):
        return self._generate_move(
            self.env.company.partner_id,
            self.partner_a,
            send=send,
            move_type=move_type,
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
            ],
        )

    def get_attachment(self, move):
        self.assertTrue(move.ubl_cii_xml_id)
        self.assertEqual(move.ubl_cii_xml_id.name[-11:], "cius_ro.xml")
        return move.ubl_cii_xml_id

    def test_export_invoice(self):
        invoice = self.create_move("out_invoice")
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice.xml')

    def test_export_credit_note(self):
        refund = self.create_move("out_refund")
        attachment = self.get_attachment(refund)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_refund.xml')

    def test_export_credit_note_with_negative_quantity(self):
        refund = self._generate_move(
            self.env.company.partner_id,
            self.partner_a,
            send=True,
            move_type="out_refund",
            currency_id=self.currency_data['currency'].id,
            invoice_line_ids=[
                {
                    'name': 'Test Product A',
                    'product_id': self.product_a.id,
                    'quantity': -1.0,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'name': 'Test Product B',
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'price_unit': 0.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'name': 'Test Downpayment',
                    'product_id': False,
                    'quantity': 1.0,
                    'price_unit': 600.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                    'is_downpayment': True,
                }
            ]
        )
        attachment = self.get_attachment(refund)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_refund_negative_quantity.xml')

    def test_export_invoice_different_currency(self):
        self.currency_data['currency'] = self.env.ref('base.USD')
        invoice = self.create_move("out_invoice")
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_different_currency.xml')
        self.currency_data['currency'] = self.env.ref('base.RON')

    def test_export_invoice_without_country_code_prefix_in_vat(self):
        self.company_data['company'].write({'vat': '1234567897'})
        self.partner_a.write({'vat': False})
        invoice = self.create_move("out_invoice")
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_no_prefix_vat.xml')

    def test_export_no_vat_but_have_company_registry(self):
        self.company_data['company'].write({'vat': False, 'company_registry': 'RO1234567897'})
        invoice = self.create_move("out_invoice")
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice.xml')

    def test_export_no_vat_but_have_company_registry_without_prefix(self):
        self.company_data['company'].write({'vat': False, 'company_registry': '1234567897'})
        self.partner_a.write({'vat': False})
        invoice = self.create_move("out_invoice")
        attachment = self.get_attachment(invoice)
        self._assert_invoice_attachment(attachment, xpaths=None, expected_file_path='from_odoo/ciusro_out_invoice_no_prefix_vat.xml')

    def test_export_no_vat_and_no_company_registry_raises_error(self):
        self.company_data['company'].write({'vat': False, 'company_registry': False})
        invoice = self.create_move("out_invoice", send=False)
        with self.assertRaisesRegex(UserError, "doesn't have a VAT nor Company ID"):
            invoice._generate_pdf_and_send_invoice(self.move_template, allow_fallback_pdf=False)

    def test_export_constraints(self):
        self.company_data['company'].company_registry = False
        for required_field in ('city', 'street', 'state_id', 'vat'):
            prev_val = self.company_data["company"][required_field]
            self.company_data["company"][required_field] = False
            invoice = self.create_move("out_invoice", send=False)
            with self.assertRaisesRegex(UserError, "required"):
                invoice._generate_pdf_and_send_invoice(self.move_template, allow_fallback_pdf=False)
            self.company_data["company"][required_field] = prev_val

        self.company_data["company"].city = "Bucharest"
        invoice = self.create_move("out_invoice", send=False)
        with self.assertRaisesRegex(UserError, "city name must be 'SECTORX'"):
            invoice._generate_pdf_and_send_invoice(self.move_template, allow_fallback_pdf=False)
