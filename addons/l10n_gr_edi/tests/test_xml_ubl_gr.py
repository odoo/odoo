from lxml import etree
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLGr(AccountTestInvoicingCommon):
    """Tests for Greek CIUS (BIS 3.0) B2G invoicing"""

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gr')
    def setUpClass(cls):
        super().setUpClass()

        # Setup Greek company
        cls.env.company.write({
            'country_id': cls.env.ref('base.gr').id,
            'name': 'Test GR Company',
            'street': 'Odos Str 10',
            'city': 'Athens',
            'zip': '10100',
            'currency_id': cls.env.ref('base.EUR').id,
            'vat': 'EL047747270',
            'l10n_gr_edi_test_env': True,
            'l10n_gr_edi_aade_id': 'odoodev',
            'l10n_gr_edi_aade_key': '20ea658627fd8c7d90594fe4601d3327',
            'peppol_endpoint': 'EL047747270',
            'peppol_eas': '9933',
        })

        # Setup Greek customer (Contracting Authority)
        cls.partner_a = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.gr').id,
            'name': 'Greek Govt customer',
            'street': 'Kallirois Str 5',
            'city': 'Athens',
            'zip': '10100',
            'vat': 'EL047747210',
            'l10n_gr_edi_contracting_authority_name': 'Ministry of justice',
            'l10n_gr_edi_contracting_authority_code': '2048.8010430600.00061',
            'peppol_endpoint': 'EL047747210',
            'peppol_eas': '9933',
        })

        # Create products with CPV codes for Greek procurement
        cls.product_a.write({
            'default_code': 'E-COM08',
            'l10n_gr_edi_cpv_code': '123123',
        })
        cls.product_b.write({
            'default_code': 'FURN_0001',
            'l10n_gr_edi_cpv_code': '243234',
        })

    def _create_gr_invoice(self, move_type='out_invoice', **invoice_kwargs):
        default_vals = {
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'invoice_date': '2025-12-17',
            'date': '2025-12-17',

            'l10n_gr_edi_budget_type': '1',
            'l10n_gr_edi_project_reference': '13213422222',
            'l10n_gr_edi_contract_reference': '0121221212',
            'l10n_gr_edi_inv_type': '1.1',

            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 15.8,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 5.1,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        }
        default_vals.update(invoice_kwargs)

        move = self.env['account.move'].create(default_vals)
        move.action_post()
        return move

    def _read_xml_test_file(self, file_name):
        with misc.file_open(f'{self.test_module}/tests/test_files/from_odoo/{file_name}.xml', 'rb') as file:
            xml_file = file.read()
        return xml_file

    def _export_ubl_gr_invoice(self, invoice):
        xml_content, _ = self.env['account.edi.xml.ubl_gr']._export_invoice(invoice)
        return xml_content

    def _get_xml_element(self, xml_content, xpath):
        root = etree.fromstring(xml_content)
        return root.find(f'.//{{{root.nsmap[None]}}}{xpath}' if root.nsmap.get(None) else f'.//{xpath}')

    def _get_xml_elements(self, xml_content, xpath):
        root = etree.fromstring(xml_content)
        return root.findall(f'.//{{{root.nsmap[None]}}}{xpath}' if root.nsmap.get(None) else f'.//{xpath}')

    # -------------------------------------------------------------------------
    # BASIC EXPORT TESTS
    # -------------------------------------------------------------------------

    def test_export_greek_invoice(self):
        invoice = self._create_gr_invoice(
            partner_id=self.partner_a.id,
            invoice_date='2025-01-01',
            l10n_gr_edi_budget_type='1',
            l10n_gr_edi_project_reference='ADA123456',
            l10n_gr_edi_contract_reference='ADAM123456',
            l10n_gr_edi_inv_type='1.1',
        )
        invoice.l10n_gr_edi_state = 'invoice_sent'
        invoice.l10n_gr_edi_mark = 400001958334210

        xml_content = self._export_ubl_gr_invoice(invoice)
        expected_xml = self._read_xml_test_file('grcius_out_invoice')

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(xml_content),
            self.get_xml_tree_from_string(expected_xml)
        )

    def test_export_greek_credit_note(self):
        """Test Greek B2G credit note export with XML fixture comparison"""
        # Create original invoice first
        original_invoice = self._create_gr_invoice(
            partner_id=self.partner_a.id,
            invoice_date='2025-01-01',
            l10n_gr_edi_budget_type='1',
            l10n_gr_edi_project_reference='ADA123456',
            l10n_gr_edi_contract_reference='ADAM123456',
            l10n_gr_edi_inv_type='1.1',
        )
        original_invoice.l10n_gr_edi_state = 'invoice_sent'
        original_invoice.l10n_gr_edi_mark = 123456789

        # Create credit note
        refund = self._create_gr_invoice(
            move_type='out_refund',
            partner_id=self.partner_a.id,
            invoice_date='2025-01-01',
            l10n_gr_edi_budget_type='1',
            l10n_gr_edi_inv_type='1.2',
        )
        refund.reversed_entry_id = original_invoice.id
        refund.l10n_gr_edi_state = 'invoice_sent'
        refund.l10n_gr_edi_mark = 123456789

        xml_content = self._export_ubl_gr_invoice(refund)
        expected_xml = self._read_xml_test_file('grcius_out_refund')

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(xml_content),
            self.get_xml_tree_from_string(expected_xml)
        )

    # -------------------------------------------------------------------------
    # GREEK INVOICE NUMBER FORMAT TESTS (GR-R-001)
    # -------------------------------------------------------------------------

    def test_greek_invoice_number_with_tax_representative(self):
        """Test invoice number format when company has tax representative"""
        tax_rep = self.env['res.partner'].create({
            'name': 'Tax Representative',
            'country_id': self.env.ref('base.gr').id,
            'vat': 'EL999999999',
        })

        self.env.company.write({
            'l10n_gr_edi_has_tax_representative': True,
            'l10n_gr_edi_tax_representative_partner_id': tax_rep.id,
        })

        invoice = self._create_gr_invoice()
        invoice.l10n_gr_edi_state = 'invoice_sent'
        invoice.l10n_gr_edi_mark = 400001958317039

        # Note: TaxRepresentativeParty is not in the current UBL template,
        # so it will fail if we try to export. This test just verifies the helper method works.
        formatted_number = self.env['account.edi.xml.ubl_gr']._format_greek_invoice_number(invoice)
        segments = formatted_number.split('|')
        # Should use tax representative's VAT
        self.assertEqual(segments[0], '999999999')

    # -------------------------------------------------------------------------
    # CREDIT NOTE TESTS
    # -------------------------------------------------------------------------

    def test_credit_note_preceding_invoice_reference(self):
        """Test BT-25: Preceding invoice reference for credit notes"""
        # Create original invoice
        original_invoice = self._create_gr_invoice(l10n_gr_edi_inv_type='1.1')
        original_invoice.l10n_gr_edi_state = 'invoice_sent'
        original_invoice.l10n_gr_edi_mark = 400001958317039

        # Create credit note
        refund = self._create_gr_invoice(
            move_type='out_refund',
            l10n_gr_edi_inv_type='1.2',
        )
        refund.reversed_entry_id = original_invoice.id
        refund.l10n_gr_edi_state = 'invoice_sent'
        refund.l10n_gr_edi_mark = 400001958317040

        xml_content = self._export_ubl_gr_invoice(refund)
        root = etree.fromstring(xml_content)

        # Find billing reference
        billing_ref = root.find('.//{*}BillingReference/{*}InvoiceDocumentReference/{*}ID')
        self.assertIsNotNone(billing_ref, "BillingReference not found in credit note")
