import copy
from unittest.mock import patch

from lxml import etree

from odoo import api
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import (
    TestUBLTRCommon,
)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLTRXMLDecode(TestUBLTRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.account_edi_xml_ubl_tr = cls.env['account.edi.xml.ubl.tr']

        # Preload all XMLs
        cls.xml_templates = {
            'satis': 'l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_sale_einvoice.xml',
            'ihracat': 'l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/ihracat_sale.xml',
            'tevkifat': 'l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_withholding_einvoice.xml',
            'ihrackayitli': 'l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_export_registered_einvoice.xml',
            'istisna': 'l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_basic_tax_exempt_einvoice.xml',
            'usd_currency': 'l10n_tr_nilvera_einvoice_extended/tests/expected_xmls/invoice_earchive_multicurrency.xml',
        }

        cls.invoice_basic_sale_einvoice_tree = cls._load_xml_tree(cls.xml_templates['satis'])
        # lxml does not accept None as prefix for default namespace in xpath queries.
        cls.ns = {k or "ns": v for k, v in cls.invoice_basic_sale_einvoice_tree.nsmap.items()}

        # ==== Partner ====
        cls.partner_tr_customer = cls.env['res.partner'].create({
            'name': 'TR Customer',
            'country_id': cls.env.ref('base.tr').id,
            'vat': '1729171602',
        })

        # ==== Bank Account ====
        cls.partner_tr_bank_account = cls.env['res.partner.bank'].create({
            'partner_id': cls.partner_tr_customer.id,
            'acc_number': 'TEST IBAN 1234',
            'currency_id': cls.env.ref('base.TRY').id,
        })

        # ==== Products ====
        cls.product_with_ctsp = cls.env['product.product'].create({
            'name': 'CTSP Product',
            'type': 'consu',
            'l10n_tr_ctsp_number': "_CTSP_TEST",
        })

        cls.product_with_default_code = cls.env['product.product'].create({
            'name': 'Default Code Product',
            'type': 'consu',
            'default_code': "_DEF_CODE_5678",
        })

    # =====================================================================
    # Helper: Load XML once
    # =====================================================================
    @classmethod
    def _load_xml_tree(cls, path):
        with file_open(path, 'rb') as xml_file:
            return etree.fromstring(xml_file.read())

    # =====================================================================
    # Helper: Return cloned tree w/ nodes removed
    # =====================================================================
    @staticmethod
    def _xml_remove_nodes(tree, xpath):
        new_tree = copy.deepcopy(tree)
        for node in new_tree.xpath(xpath, namespaces=TestUBLTRXMLDecode.ns):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
        return new_tree

    @staticmethod
    def _update_xpath_text(tree, xpath, new_value):
        new_tree = copy.deepcopy(tree)
        for node in new_tree.xpath(xpath, namespaces=TestUBLTRXMLDecode.ns):
            node.text = new_value
        return new_tree

    # =====================================================================
    # Helper: Create invoice template
    # =====================================================================
    @api.model
    def _create_invoice(self, move_type='out_invoice'):
        return self.env['account.move'].create({
            'move_type': move_type,
        })

    # =====================================================================
    # BASIC PROVIDED TESTS
    # =====================================================================

    def test_l10n_tr_nilvera_uuid_field_is_set(self):
        invoice = self._create_invoice()
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree, './/cbc:UUID', 'UUID_TEST_VALUE')
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertEqual(
            invoice.l10n_tr_nilvera_uuid,
            'UUID_TEST_VALUE',
            'The UUID field was not set correctly from the XML.',
        )

    def test_node_name_mapping_is_correct(self):
        tree = copy.deepcopy(self.invoice_basic_sale_einvoice_tree)
        profile_id_node = tree.find('.//cbc:ProfileID', namespaces=self.ns)

        # IHRACAT → BuyerCustomer
        profile_id_node.text = 'IHRACAT'
        node_name = self.account_edi_xml_ubl_tr._get_partner_node_name(tree)
        self.assertEqual(node_name, 'BuyerCustomer', 'IHRACAT profile should map to BuyerCustomer node.')

        # Other → AccountingCustomer
        profile_id_node.text = 'random'
        node_name = self.account_edi_xml_ubl_tr._get_partner_node_name(tree)
        self.assertEqual(node_name, 'AccountingCustomer', 'Other profiles should map to AccountingCustomer node.')

        profile_id_node.text = ''
        node_name = self.account_edi_xml_ubl_tr._get_partner_node_name(tree)
        self.assertEqual(node_name, 'AccountingCustomer', 'Empty profile should map to AccountingCustomer node.')

    def test_partner_not_set_if_vkn_missing(self):
        tree = self._xml_remove_nodes(self.invoice_basic_sale_einvoice_tree,
                                      './/cac:PartyLegalEntity//cbc:CompanyID')
        tree = self._xml_remove_nodes(tree, './/cac:PartyIdentification//cbc:ID[@schemeID="VKN"]')

        partner_id = self.account_edi_xml_ubl_tr._resolve_invoice_partner(
            tree, self.partner_tr_customer.company_id, {}, [])

        self.assertFalse(partner_id, 'No partner should be set when VAT/VKN is missing.')

    def test_fetch_existing_partner_by_vkn(self):
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree,
                                       './/cac:PartyLegalEntity//cbc:CompanyID', self.partner_tr_customer.vat)

        partner_id = self.account_edi_xml_ubl_tr._resolve_invoice_partner(
            tree, self.partner_tr_customer.company_id, {}, [])

        self.assertEqual(partner_id.id, self.partner_tr_customer.id, 'Should fetch existing partner by VAT/VKN.')

    @patch('odoo.addons.l10n_tr_nilvera.models.res_partner.ResPartner.l10n_tr_check_nilvera_customer')
    @patch('odoo.addons.base_vat.models.res_partner.ResPartner._inverse_vat', new=lambda self: None)
    def test_create_new_partner_and_verify_when_not_existing_vkn(self, l10n_tr_check_nilvera_customer_mocked):
        new_vat = '0123456789000'
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree,
                                       './/cac:PartyLegalEntity//cbc:CompanyID', new_vat)

        non_existing_partner = self.env['res.partner'].search([('vat', '=', new_vat)])
        self.assertFalse(non_existing_partner, 'Partner with new VAT should not exist before test.')

        partner_id = self.account_edi_xml_ubl_tr._resolve_invoice_partner(
            tree, self.partner_tr_customer.company_id, {}, [])

        new_created_partner = self.env['res.partner'].search([('vat', '=', new_vat)])

        self.assertEqual(partner_id.id, new_created_partner.id,
                         'Should create and set new partner based on VAT/VKN.')

        l10n_tr_check_nilvera_customer_mocked.assert_called_once()

    def test_import_works_without_invoice_lines(self):
        tree = self._xml_remove_nodes(self.invoice_basic_sale_einvoice_tree, './/cac:InvoiceLine')
        invoice = self._create_invoice()

        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertFalse(invoice.invoice_line_ids)
        # Any other fields is set correctly, meaning the invoice is created without lines
        self.assertTrue(invoice.partner_id)

    def test_no_bank_account_when_payment_means_missing(self):
        tree = self._xml_remove_nodes(self.invoice_basic_sale_einvoice_tree, './/cac:PaymentMeans')
        partner = self.env.company.partner_id
        vals = {}
        self.account_edi_xml_ubl_tr._resolve_bank_account(tree, partner, vals, [])
        self.assertNotIn('partner_bank_id', vals, 'No bank account should be set if PaymentMeans is missing.')

    def test_existing_bank_account_detected_by_acc_number(self):
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree,
                                       './/cac:PaymentMeans//cac:PayeeFinancialAccount//cbc:ID',
                                       self.partner_tr_bank_account.acc_number)
        partner = self.partner_tr_customer
        vals = {}
        self.account_edi_xml_ubl_tr._resolve_bank_account(tree, partner, vals, [])

        self.assertEqual(vals.get('partner_bank_id'), self.partner_tr_bank_account.id,
                         'Should fetch existing bank account based on account no.')

    def test_new_bank_account_created_if_not_existing(self):
        new_iban = 'NEW-IBAN-5678'
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree,
                                       './/cac:PaymentMeans//cac:PayeeFinancialAccount//cbc:ID',
                                       new_iban)

        non_existing_bank_account = self.env['res.partner.bank'].search([
            ('partner_id', '=', self.partner_tr_customer.id),
            ('acc_number', '=', new_iban),
        ])
        self.assertFalse(non_existing_bank_account, 'Bank account with new IBAN should not exist before test.')

        partner = self.partner_tr_customer
        vals = {}
        self.account_edi_xml_ubl_tr._resolve_bank_account(tree, partner, vals, [])

        new_created_bank_account = self.env['res.partner.bank'].search([
            ('partner_id', '=', self.partner_tr_customer.id),
            ('acc_number', '=', new_iban),
        ])

        self.assertEqual(vals.get('partner_bank_id'), new_created_bank_account.id,
                         'Should create and set new bank account based on IBAN.')
        self.assertEqual(new_created_bank_account.partner_id.id, self.partner_tr_customer.id,
                         'New bank account should be linked to the correct partner.')

    def test_product_resolution_by_ctsp_number(self):
        ihracat_tree = self._load_xml_tree(self.xml_templates['ihracat'])
        tree = self._update_xpath_text(ihracat_tree,
                                       './/cac:InvoiceLine//cac:Delivery//cac:Shipment//cbc:RequiredCustomsID',
                                       self.product_with_ctsp.l10n_tr_ctsp_number)

        vals = {}
        self.account_edi_xml_ubl_tr._resolve_invoice_lines(tree, vals, 'sale', [])

        self.assertIn('invoice_line_ids', vals, 'invoice_line_ids should be in vals after resolving invoice lines.')
        first_line = vals['invoice_line_ids'][0][2]
        self.assertEqual(first_line.get('product_id'), self.product_with_ctsp.id,
                         'Product should be resolved by CTSP number.')

    def test_product_resolution_by_default_code(self):
        ihracat_tree = self._load_xml_tree(self.xml_templates['ihracat'])
        tree = self._update_xpath_text(ihracat_tree,
                                       './/cac:InvoiceLine//cac:Item//cac:SellersItemIdentification//cbc:ID',
                                       self.product_with_default_code.default_code)

        vals = {}
        self.account_edi_xml_ubl_tr._resolve_invoice_lines(tree, vals, 'sale', [])

        self.assertIn('invoice_line_ids', vals, 'invoice_line_ids should be in vals after resolving invoice lines.')
        first_line = vals['invoice_line_ids'][0][2]
        self.assertEqual(first_line.get('product_id'), self.product_with_default_code.id,
                         'Product should be resolved by default code.')

    def test_product_resolution_fallback_to_name(self):
        ihracat_tree = self._load_xml_tree(self.xml_templates['ihracat'])
        tree = self._update_xpath_text(ihracat_tree,
                                       './/cac:InvoiceLine//cac:Item//cbc:Description',
                                       'Fallback Product Name')

        vals = {}
        self.account_edi_xml_ubl_tr._resolve_invoice_lines(tree, vals, 'sale', [])

        self.assertIn('invoice_line_ids', vals, 'invoice_line_ids should be in vals after resolving invoice lines.')
        first_line = vals['invoice_line_ids'][0][2]
        self.assertFalse(first_line.get('product_id'),
                         'Product should not be resolved by CTSP or default code, fallback to name used.')
        self.assertEqual(first_line.get('name'), 'Fallback Product Name',
                         'Product name should be set from the XML description.')

    def test_multi_currency_is_set_from_xml(self):
        tree = self._load_xml_tree(self.xml_templates['usd_currency'])
        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)
        self.assertEqual(invoice.currency_id.name, 'USD', 'Invoice currency should be set to USD from XML.')

    def test_innactive_invoice_currency_is_set_active(self):
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree, './/cbc:DocumentCurrencyCode', 'BDT')
        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)
        self.assertTrue(invoice.currency_id.active, 'Inactive currency should be set active when used in invoice.')

    # =====================================================================
    # Invoice Scenarios
    # =====================================================================

    # SATIS(Sale)
    # =====================================================================
    def test_import_satis(self):
        invoice = self._create_invoice()
        tree = copy.deepcopy(self.invoice_basic_sale_einvoice_tree)

        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertFalse(invoice.l10n_tr_is_export_invoice, 'satis should not be marked as export invoice.')
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'SATIS', 'Invoice type should be SATIS.')

        self.assertTrue(invoice.invoice_line_ids, 'There should be invoice lines.')
        first_line = invoice.invoice_line_ids[0]

        # tax should not be zero
        self.assertTrue(first_line.tax_ids, 'There should be taxes on the line.')
        self.assertNotEqual(first_line.tax_ids.amount, 0.0, 'temelfatura_satis should have non-zero tax.')

        # Discount field is set
        # Not mandatory, but xml has it. So, check if it's set.
        self.assertGreaterEqual(first_line.discount, 1, 'Discount field should be set on the line.')

    # TEVKIFAT (WITHHOLDING)
    # =====================================================================
    def test_import_tevkifat(self):
        invoice = self._create_invoice()
        tree = self._load_xml_tree(self.xml_templates['tevkifat'])

        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertFalse(invoice.l10n_tr_is_export_invoice, 'Should not be an export invoice.')
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'TEVKIFAT', 'Invoice type should be TEVKIFAT.')

        self.assertTrue(invoice.invoice_line_ids, 'There should be invoice lines.')
        first_line = invoice.invoice_line_ids[0]

        self.assertTrue(first_line.tax_ids)
        self.assertTrue(first_line.tax_ids.children_tax_ids, 'There should be child taxes for withholding.')

        withholding_taxes = first_line.tax_ids.children_tax_ids.filtered('l10n_tr_tax_withholding_code_id')
        self.assertTrue(withholding_taxes, 'tevkifat should be a tax with withholding reason')

    # IHRACKAYITLI (Registered for Export)
    # =====================================================================
    def test_import_ihrackayitli(self):
        invoice = self._create_invoice()
        tree = self._load_xml_tree(self.xml_templates['ihrackayitli'])

        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertFalse(invoice.l10n_tr_is_export_invoice, 'Should not be an export invoice.')
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'IHRACKAYITLI', 'Invoice type should be IHRACKAYITLI.')
        self.assertTrue(invoice.l10n_tr_exemption_code_id, 'ihrackayitli should have an exemption code set.')

        self.assertTrue(invoice.invoice_line_ids, 'There should be invoice lines.')
        first_line = invoice.invoice_line_ids[0]

        self.assertTrue(first_line.tax_ids)

    # ISTISNA (Tax Exempt)
    # =====================================================================
    def test_import_istisna(self):
        invoice = self._create_invoice()
        tree = self._load_xml_tree(self.xml_templates['istisna'])

        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertFalse(invoice.l10n_tr_is_export_invoice, 'Should not be an export invoice.')
        self.assertEqual(invoice.l10n_tr_gib_invoice_type, 'ISTISNA', 'Invoice type should be ISTISNA.')
        self.assertTrue(invoice.l10n_tr_exemption_code_id, 'istisna should have an exemption code set.')

        self.assertTrue(invoice.invoice_line_ids, 'There should be invoice lines.')
        first_line = invoice.invoice_line_ids[0]

        self.assertTrue(first_line.tax_ids)

    # IHRACAT (EXPORT)
    # =====================================================================
    def test_import_ihracat_export_invoice(self):
        invoice = self._create_invoice()
        tree = self._load_xml_tree(self.xml_templates['ihracat'])

        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertTrue(invoice.l10n_tr_is_export_invoice, 'ihracat should be marked as export invoice.')
        self.assertTrue(invoice.l10n_tr_exemption_code_id, 'ihracat should have an exemption code set.')
        self.assertTrue(invoice.l10n_tr_shipping_type, 'ihracat should have a shipping type set.')
        self.assertTrue(invoice.invoice_incoterm_id, 'Incoterm should be set for export invoice.')

        self.assertTrue(invoice.invoice_line_ids, 'There should be invoice lines.')
        for line in invoice.invoice_line_ids:
            if line.tax_ids:
                self.assertEqual(line.tax_ids.amount, 0.0, 'Export invoice lines should have 0% tax.')

    def test_credit_note_not_supported_logs_error(self):
        invoice = self._create_invoice()
        tree = copy.deepcopy(self.invoice_basic_sale_einvoice_tree)

        logs = self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, qty_factor=-1)

        self.assertTrue(any(
            'invoice/bill return creation from xml is not supported for tr1.2 ubl format yet.' in log.lower() for log in
            logs))

    # =====================================================================
    # FALLBACK → IF CustomizationID != TR1.2
    # =====================================================================

    @patch('odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20.AccountEdiXmlUbl_20._import_fill_invoice')
    def test_fallback_to_super_when_not_ubl_tr(self, _import_fill_invoice_mocked):
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree, './/cbc:CustomizationID',
                                       'OTHER-VERSION')
        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)
        _import_fill_invoice_mocked.assert_called_once()
