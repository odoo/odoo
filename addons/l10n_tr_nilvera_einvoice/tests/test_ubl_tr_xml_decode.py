import copy
from unittest.mock import patch

from lxml import etree

from odoo import api
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES
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
            'satis': 'l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_sale_einvoice.xml',
            'ihracat': 'l10n_tr_nilvera_einvoice/tests/expected_xmls/ihracat_istisna.xml',
            'tevkifat': 'l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_withholding_einvoice.xml',
            'ihrackayitli': 'l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_export_registered_einvoice.xml',
            'istisna': 'l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_basic_tax_exempt_einvoice.xml',
            'usd_currency': 'l10n_tr_nilvera_einvoice/tests/expected_xmls/invoice_earchive_multicurrency.xml',
        }

        cls.invoice_basic_sale_einvoice_tree = cls._load_xml_tree(cls.xml_templates['satis'])

        # ==== Partner ====
        cls.partner_tr_customer = cls.env['res.partner'].create({
            'name': 'TR Customer',
            'country_id': cls.env.ref('base.tr').id,
            'vat': '1729171602',
        })

        # ==== Bank Account ====
        cls.partner_tr_bank_account = cls.env['res.partner.bank'].create({
            'partner_id': cls.partner_tr_customer.id,
            'account_number': 'TESTIBAN1234',
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
        for node in new_tree.xpath(xpath, namespaces=UBL_NAMESPACES):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
        return new_tree

    @staticmethod
    def _update_xpath_text(tree, xpath, new_value):
        new_tree = copy.deepcopy(tree)
        for node in new_tree.xpath(xpath, namespaces=UBL_NAMESPACES):
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
        profile_id_node = tree.find('.//cbc:ProfileID', namespaces=UBL_NAMESPACES)

        # IHRACAT → BuyerCustomer
        profile_id_node.text = 'IHRACAT'
        node_name = self.account_edi_xml_ubl_tr._l10n_tr_import_party_role(tree)
        self.assertEqual(node_name, 'BuyerCustomer', 'IHRACAT profile should map to BuyerCustomer node.')

        # Sale
        # Other → AccountingCustomer
        profile_id_node.text = 'random'
        node_name = self.account_edi_xml_ubl_tr._l10n_tr_import_party_role(tree, 'sale')
        self.assertEqual(node_name, 'AccountingCustomer', 'Other profiles should map to AccountingCustomer node for sale.')

        profile_id_node.text = ''
        node_name = self.account_edi_xml_ubl_tr._l10n_tr_import_party_role(tree, 'sale')
        self.assertEqual(node_name, 'AccountingCustomer', 'Empty profile should map to AccountingCustomer node for sale.')

        # Purchase
        # Other → AccountingCustomer
        profile_id_node.text = 'random'
        node_name = self.account_edi_xml_ubl_tr._l10n_tr_import_party_role(tree, 'purchase')
        self.assertEqual(node_name, 'AccountingSupplier', 'Other profiles should map to AccountingCustomer node for purchase.')

        profile_id_node.text = ''
        node_name = self.account_edi_xml_ubl_tr._l10n_tr_import_party_role(tree, 'purchase')
        self.assertEqual(node_name, 'AccountingSupplier', 'Empty profile should map to AccountingCustomer node for purchase.')

    def test_fetch_existing_partner_by_vkn(self):
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree,
                                       './/cac:PartyLegalEntity//cbc:CompanyID', self.partner_tr_customer.vat)
        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertEqual(invoice.partner_id.id, self.partner_tr_customer.id, 'Should fetch existing partner by VAT/VKN.')

    @patch('odoo.addons.l10n_tr_nilvera.models.res_partner.ResPartner.l10n_tr_check_nilvera_customer')
    @patch('odoo.addons.base_vat.models.res_partner.ResPartner._inverse_vat', new=lambda self: None)
    def test_create_new_partner_and_verify_when_not_existing_vkn(self, l10n_tr_check_nilvera_customer_mocked):
        new_vat = '0123456789000'
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree,
                                       './/cac:PartyLegalEntity//cbc:CompanyID', new_vat)

        non_existing_partner = self.env['res.partner'].search([('vat', '=', new_vat)])
        self.assertFalse(non_existing_partner, 'Partner with new VAT should not exist before test.')

        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        new_created_partner = self.env['res.partner'].search([('vat', '=', new_vat)])

        self.assertEqual(invoice.partner_id.id, new_created_partner.id,
                         'Should create and set new partner based on VAT/VKN.')

        l10n_tr_check_nilvera_customer_mocked.assert_called_once()

    def test_existing_bank_account_detected_by_account_number(self):
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree,
                                       './/cac:PaymentMeans//cac:PayeeFinancialAccount//cbc:ID',
                                       self.partner_tr_bank_account.account_number)
        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertEqual(invoice.partner_bank_id.id, self.partner_tr_bank_account.id,
                         'Should fetch existing bank account based on account no.')

    def test_new_bank_account_created_if_not_existing(self):
        new_iban = 'NEW-IBAN-5678'
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree,
                                       './/cac:PaymentMeans//cac:PayeeFinancialAccount//cbc:ID',
                                       new_iban)

        non_existing_bank_account = self.env['res.partner.bank'].search([
            ('partner_id', '=', self.partner_tr_customer.id),
            ('account_number', '=', new_iban),
        ])
        self.assertFalse(non_existing_bank_account, 'Bank account with new IBAN should not exist before test.')

        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        new_created_bank_account = self.env['res.partner.bank'].search([
            ('partner_id', '=', self.partner_tr_customer.id),
            ('account_number', '=', new_iban),
        ])

        self.assertEqual(invoice.partner_bank_id.id, new_created_bank_account.id,
                         'Should create and set new bank account based on IBAN.')
        self.assertEqual(new_created_bank_account.partner_id.id, self.partner_tr_customer.id,
                         'New bank account should be linked to the correct partner.')

    def test_product_resolution_by_ctsp_number(self):
        ihracat_tree = self._load_xml_tree(self.xml_templates['ihracat'])
        tree = self._update_xpath_text(ihracat_tree,
                                       './/cac:InvoiceLine//cac:Delivery//cac:Shipment//cbc:RequiredCustomsID',
                                       self.product_with_ctsp.l10n_tr_ctsp_number)

        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        product_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_name.endswith('Discount'))
        self.assertEqual(product_lines[:1].product_id.id, self.product_with_ctsp.id,
                         'Product should be resolved by CTSP number.')

    def test_product_resolution_by_default_code(self):
        ihracat_tree = self._load_xml_tree(self.xml_templates['ihracat'])
        tree = self._update_xpath_text(ihracat_tree,
                                       './/cac:InvoiceLine//cac:Item//cac:SellersItemIdentification//cbc:ID',
                                       self.product_with_default_code.default_code)

        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        product_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_name.endswith("Discount"))
        self.assertEqual(product_lines[:1].product_id.id, self.product_with_default_code.id,
                         'Product should be resolved by default code.')

    def test_product_resolution_fallback_to_name(self):
        ihracat_tree = self._load_xml_tree(self.xml_templates['ihracat'])
        tree = self._update_xpath_text(ihracat_tree,
                                       './/cac:InvoiceLine//cac:Item//cbc:Description',
                                       'Fallback Product Name')

        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        product_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_name.endswith("Discount"))
        self.assertFalse(product_lines[:1].product_id, 'Product should not be resolved')
        self.assertTrue(product_lines[:1].display_name, 'Fallback Product Name should be set as line description.')

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
        non_discount_lines = invoice.invoice_line_ids.filtered(
            lambda l: not l.display_name.endswith("Discount")
        )
        first_line = non_discount_lines[:1]

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
        non_discount_lines = invoice.invoice_line_ids.filtered(
            lambda l: not l.display_name.endswith("Discount")
        )
        first_line = non_discount_lines[:1]

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
        non_discount_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_name.endswith('Discount'))
        first_line = non_discount_lines[:1]

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
        non_discount_lines = invoice.invoice_line_ids.filtered(lambda l: not l.display_name.endswith('Discount'))
        first_line = non_discount_lines[:1]

        self.assertTrue(first_line.tax_ids)

    # IHRACAT (EXPORT)
    # =====================================================================
    def test_import_ihracat_export_invoice(self):
        invoice = self._create_invoice()
        tree = self._load_xml_tree(self.xml_templates['ihracat'])

        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)

        self.assertEqual(invoice.partner_id.name, 'earchive_partner', 'Partner name is not correctly imported')
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

    @patch('odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20.AccountEdiXmlUBL20._import_fill_invoice')
    def test_fallback_to_super_when_not_ubl_tr(self, _import_fill_invoice_mocked):
        tree = self._update_xpath_text(self.invoice_basic_sale_einvoice_tree, './/cbc:CustomizationID',
                                       'OTHER-VERSION')
        invoice = self._create_invoice()
        self.account_edi_xml_ubl_tr._import_fill_invoice(invoice, tree, 1)
        _import_fill_invoice_mocked.assert_called_once()
