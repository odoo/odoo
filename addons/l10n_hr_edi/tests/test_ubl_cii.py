from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install', 'l10n_hr_edi')
class TestL10nHrEdiXml(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        cls.env.company.tax_calculation_rounding_method = 'round_globally'
        cls.partner_a.invoice_edi_format = 'ubl_bis3'

        cls.pay_term_epd_mixed = cls.env['account.payment.term'].create({
            'name': "2/7 Net 30",
            'note': "Payment terms: 30 Days, 2% Early Payment Discount under 7 days",
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 7,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30})],
        })

    @classmethod
    def _create_company(cls, **create_values):
        # EXTENDS 'account'
        create_values['currency_id'] = cls.env.ref('base.EUR').id
        create_values['country_id'] = cls.env.ref('base.hr').id
        return super()._create_company(**create_values)

    def setup_partner_as_hr(self, partner):
        partner.write({
            'street': "Croatian Street 1",
            'zip': "1234",
            'city': "Croatian City",
            'vat': 'HR01234567896',
            'company_registry': '0000000001',
            'country_id': self.env.ref('base.hr').id,
            'bank_ids': [Command.create({'acc_number': 'HR10000000000000'})],
            'email': 'test1@test.test',
        })

    def setup_partner_as_be(self, partner):
        partner.write({
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'company_registry': '0477472701',
            'country_id': self.env.ref('base.be').id,
            'bank_ids': [Command.create({'acc_number': 'BE90735788866632'})],
            'email': 'test2@test.test',
        })

    def test_export_invoice_from_account_edi_xml_ubl_hr(self):
        """ Test content of a generated basic invoice. This may require adjustments for Peppol implementation.
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_be(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        actual_content, _dummy = self.env['account.edi.xml.ubl_hr'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )

    def test_export_invoice_with_exemption(self):
        """ Test the content of a generated invoice with VAT exemption. This may require adjustments for Peppol implementation.
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_be(self.partner_a)
        tax_exe = self.percent_tax(0.0)
        tax_exe.l10n_hr_vat_expence_category_id = self.env.ref('l10n_hr_edi.vat_type_pp')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_exe.ids)],
                }),
            ],
        })
        invoice.action_post()
        actual_content, _dummy = self.env['account.edi.xml.ubl_hr'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_exemption.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )

    def test_export_invoice_with_refund(self):
        """ Test content of a generated credit note. This may require adjustments for Peppol implementation.
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_be(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        actual_content, _dummy = self.env['account.edi.xml.ubl_hr'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_refund.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )
