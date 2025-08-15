from odoo import Command
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLRS(TestUBLCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="rs"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.rs').id,
            'currency_id': cls.env.ref('base.RSD').id,
            'name': 'Test RS Company',
            'city': 'Niš',
            'zip': '12000',
            'vat': 'RS101134702',
            'phone': '+381 23 456 78 91',
            'street': 'Nikole Pašića 30a',
            'invoice_is_ubl_cii': True,
        })
        cls.company_data['company'].partner_id.l10n_rs_edi_registration_number = '87654321'

        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'RS1234123456123456123456',
        })

        cls.partner_a = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.rs').id,
            'name': 'Serbian Customer',
            'city': 'Belgrade',
            'street': 'Balkanska ulica, 21',
            'zip': '101801',
            'phone': '+381 98 765 43 21',
            'vat': 'RS111032440',
            'bank_ids': [Command.create({'acc_number': 'RS1234567891234567892345'})],
            'l10n_rs_edi_registration_number': '12345678',
        })

    def create_invoice(self, move_type, **invoice_kwargs):
        return self._generate_move(
            self.env.company.partner_id,
            self.partner_a,
            send=False,
            move_type=move_type,
            currency_id=self.env.company.currency_id.id,
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                },
            ],
            **invoice_kwargs,
        )

    def _read_xml_test_file(self, file_name):
        with misc.file_open(f'{self.test_module}/tests/test_files/{file_name}.xml', 'rb') as file:
            xml_file = file.read()
        return xml_file

    def test_export_invoice(self):
        invoice = self.create_invoice("out_invoice")
        invoice_xml, _ = self.env['account.edi.xml.ubl.rs']._export_invoice(invoice)
        expected_xml = self._read_xml_test_file('export_invoice')
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(invoice_xml),
            self.get_xml_tree_from_string(expected_xml)
        )

    def test_export_credit_note(self):
        refund = self.create_invoice("out_refund")
        refund_xml, _ = self.env['account.edi.xml.ubl.rs']._export_invoice(refund)
        expected_xml = self._read_xml_test_file('export_credit_note')
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(refund_xml),
            self.get_xml_tree_from_string(expected_xml)
        )
