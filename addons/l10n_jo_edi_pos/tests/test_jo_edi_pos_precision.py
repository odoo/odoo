from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_jo_edi.tests.test_jo_edi_precision import TestJoEdiPrecision
from odoo.addons.l10n_jo_edi_pos.tests.jo_edi_pos_common import JoEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestJoEdiPosPrecision(JoEdiPosCommon, TestJoEdiPrecision):
    def _validate_order_vals_jo_edi_pos_numbers(self, order_vals):
        with self.subTest(sub_test_name=order_vals['name']):
            order = self._l10n_jo_create_order(order_vals)
            generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
            errors = self._validate_jo_edi_numbers(generated_file, order.amount_total)
            self.assertFalse(errors, errors)

    def test_jo_pos_sales_invoice_precision(self):
        eur = self.env.ref('base.EUR')
        self.setup_currency_rate(eur, 1.41)
        self.company.l10n_jo_edi_taxpayer_type = 'sales'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'

        self._validate_order_vals_jo_edi_pos_numbers({
            'name': 'TestEIN022',
            'currency_id': eur.id,
            'date_order': '2023-11-12',
            'lines': [
                {
                    'product_id': self.product_a.id,
                    'qty': 3.48,
                    'price_unit': 1.56,
                    'discount': 2.5,
                    'tax_ids': [Command.set(self.jo_general_tax_16_included.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'qty': 6.02,
                    'price_unit': 2.79,
                    'discount': 2.5,
                    'tax_ids': [Command.set(self.jo_general_tax_16_included.ids)],
                },
            ],
        })

    def test_jo_pos_special_invoice_precision(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'
        self._validate_order_vals_jo_edi_pos_numbers({
            'name': 'TestEIN014',
            'date_order': '2023-11-10',
            'lines': [
                {
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'qty': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_10 | self.jo_special_tax_10).ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                    'qty': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_10 | self.jo_special_tax_5).ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                    'qty': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_16 | self.jo_special_tax_5).ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'qty': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_16 | self.jo_special_tax_10).ids)],
                },
            ],
        })

    def test_jo_pos_credit_notes_price_unit(self):
        def get_price_units(xml_string):
            root = self.get_xml_tree_from_string(xml_string)
            for xml_line in root.findall('./{*}InvoiceLine'):
                yield float(xml_line.findtext('{*}Price/{*}PriceAmount'))
        self.company.l10n_jo_edi_taxpayer_type = 'sales'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'
        order = self._l10n_jo_create_order({
            'name': 'TestEIN014',
            'date_order': '2023-11-10',
            'lines': [
                {
                    'product_id': self.product_b.id,
                    'price_unit': 11.11,
                    'qty': 9833,
                    'discount': 3.12,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'price_unit': 10000.01,
                    'qty': 93333,
                    'discount': 99.71,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'price_unit': 0.01,
                    'qty': 0.11,
                    'discount': 2,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                },
            ],
        })
        refund = self._l10n_jo_create_order_refund(order, {
            'l10n_jo_edi_pos_return_reason': 'return reason',
            'lines': [
                {
                    'product_id': self.product_b.id,
                    'price_unit': 11.11,
                    'qty': 3.11,
                    'discount': 3.12,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'price_unit': 10000.01,
                    'qty': 2.02,
                    'discount': 99.71,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                },
                {
                    'product_id': self.product_a.id,
                    'price_unit': 0.01,
                    'qty': 0.1,
                    'discount': 2,
                    'tax_ids': [Command.set((self.jo_general_tax_16_included).ids)],
                },
            ],
        })
        invoice_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
        refund_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(refund)[0]
        for invoice_price_unit, refund_price_unit in zip(get_price_units(invoice_file), get_price_units(refund_file)):
            self.assertEqual(invoice_price_unit, refund_price_unit)
