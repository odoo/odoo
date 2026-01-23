from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_hr_edi.tests.test_hr_edi_common import TestL10nHrEdiCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install', 'l10n_hr_edi_xml')
class TestL10nHrEdiXml(TestL10nHrEdiCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.partner_id.l10n_hr_business_unit_code = '12345'

    def test_export_invoice_from_account_edi_xml_ubl_hr(self):
        """
        Test content of a generated basic invoice in Croation UBL format.
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_hr_alt(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_IN_ROC_25')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'l10n_hr_process_type': 'P99',
            'l10n_hr_customer_defined_process_name': 'Test custom process type',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        # Manually create the addendum which normally happens during sending
        invoice.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
            'move_id': invoice.id,
            'invoice_sending_time': '2025-01-02',
            'fiscalization_number': self.env['account.move']._get_l10n_hr_fiscalization_number(invoice.name),
        })
        actual_content, _dummy = self.env['account.edi.xml.ubl_hr'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )

    def test_export_invoice_with_cash_basis(self):
        """
        Test content of a generated invoice with an 'on_payment' exigibility tax in Croation UBL format.
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_hr_alt(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_IN_ROC_25')
        tax.tax_exigibility = 'on_payment'

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'l10n_hr_process_type': 'P99',
            'l10n_hr_customer_defined_process_name': 'Test custom process type',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
            'move_id': invoice.id,
            'invoice_sending_time': '2025-01-02',
            'fiscalization_number': self.env['account.move']._get_l10n_hr_fiscalization_number(invoice.name),
        })
        actual_content, _dummy = self.env['account.edi.xml.ubl_hr'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_cash_basis.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )

    def test_export_invoice_with_exemption_k(self):
        """
        Test the content of a generated invoice with HR:K exemption in Croation UBL format.
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_hr_alt(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_EU_G')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
            'move_id': invoice.id,
            'invoice_sending_time': '2025-01-02',
            'fiscalization_number': self.env['account.move']._get_l10n_hr_fiscalization_number(invoice.name),
        })
        actual_content, _dummy = self.env['account.edi.xml.ubl_hr'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_exemption_k.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )

    def test_export_invoice_with_exemption_e(self):
        """
        Test the content of a generated invoice with HR:E exemption in Croation UBL format.
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_hr_alt(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_other_exempt_O')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
            'move_id': invoice.id,
            'invoice_sending_time': '2025-01-02',
            'fiscalization_number': self.env['account.move']._get_l10n_hr_fiscalization_number(invoice.name),
        })
        actual_content, _dummy = self.env['account.edi.xml.ubl_hr'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_exemption_e.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )

    def test_export_invoice_with_refund(self):
        """
        Test content of a generated credit note in Croation UBL format.
        """
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_hr_alt(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_IN_ROC_25')

        invoice = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-01-01',
            'l10n_hr_process_type': 'P9',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()
        invoice.l10n_hr_edi_addendum_id = self.env['l10n_hr_edi.addendum'].create({
            'move_id': invoice.id,
            'invoice_sending_time': '2025-01-02',
            'fiscalization_number': self.env['account.move']._get_l10n_hr_fiscalization_number(invoice.name),
        })
        actual_content, _dummy = self.env['account.edi.xml.ubl_hr'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/test_invoice_refund.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )
