from lxml import etree

from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiNOCommon
from odoo.tests import tagged

UBL_NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
}


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblExportBis3NO(TestUblBis3Common, TestUblCiiNOCommon):

    _test_groups = None  # FIXME list needed groups

    def _export_invoice_xml(self, vat):
        self.env.company.partner_id.vat = vat
        tax_25 = self.percent_tax(25.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_25)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )
        xml_bytes, errors = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)
        self.assertFalse(errors, f"Unexpected export errors: {errors}")
        return etree.fromstring(xml_bytes)

    def _assert_supplier_vat_nodes(self, root, expected_vat):
        supplier_party = root.find('.//cac:AccountingSupplierParty/cac:Party', UBL_NS)

        vat_scheme = next(
            node for node in supplier_party.findall('cac:PartyTaxScheme', UBL_NS)
            if node.findtext('cac:TaxScheme/cbc:ID', namespaces=UBL_NS) == 'VAT'
        )
        self.assertEqual(vat_scheme.findtext('cbc:CompanyID', namespaces=UBL_NS), expected_vat)

        tax_scheme = next(
            node for node in supplier_party.findall('cac:PartyTaxScheme', UBL_NS)
            if node.findtext('cac:TaxScheme/cbc:ID', namespaces=UBL_NS) == 'TAX'
        )
        self.assertEqual(tax_scheme.findtext('cbc:CompanyID', namespaces=UBL_NS), 'Foretaksregisteret')

        # Note: NO-R-001 constraint only affects the CompanyID within the PartyTaxScheme node, not the LegalEntity/CompanyID node.

    def test_invoice_supplier_vat_full_format(self):
        # Supplier VAT already in full NO...MVA format.
        # PartyTaxScheme/CompanyID and PartyLegalEntity/CompanyID must be NO179728982MVA.
        # NO-R-001 constraint must not raise an error.
        root = self._export_invoice_xml('NO179728982MVA')
        self._assert_supplier_vat_nodes(root, 'NO179728982MVA')

    def test_invoice_supplier_vat_bare_number(self):
        # Supplier VAT entered as bare 9-digit number without NO prefix or MVA suffix.
        # The export must auto-complete it to NO179728982MVA.
        # PartyTaxScheme/CompanyID and PartyLegalEntity/CompanyID must be NO179728982MVA.
        # NO-R-001 constraint must not raise an error.
        root = self._export_invoice_xml('995525828')
        self._assert_supplier_vat_nodes(root, 'NO995525828MVA')
