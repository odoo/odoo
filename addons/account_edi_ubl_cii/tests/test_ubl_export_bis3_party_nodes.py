from lxml import etree

from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblExportBis3PartyNodes(TestUblBis3Common, TestUblCiiBECommon):
    """Assert the four party-identification nodes of a Peppol BIS3 invoice for every country whose
    party export is special-cased, so each stays EN16931 + Peppol schematron valid when routed to
    the access point:

    - cbc:EndpointID (BT-49/BT-34, [PEPPOL-EN16931-R010/R020])
    - cac:PartyIdentification/cbc:ID (BT-29/BT-46)
    - cac:PartyLegalEntity/cbc:CompanyID (BT-30/BT-47)
    - cac:PartyTaxScheme/cbc:CompanyID (BT-31/BT-48)
    """
    _test_groups = None  # FIXME list needed groups

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _generate_party_nodes(self, partner, role='Customer'):
        """Export a BIS3 invoice for ``partner`` and return the role's party nodes.

        Asserts the EN16931/BIS3 export constraints pass (no ``errors``) so the document would be
        accepted by the schematron at the access point.
        """
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=partner,
            post=True,
        )
        xml_bytes, errors = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)
        self.assertFalse(errors, f"BIS3/EN16931 export constraints failed: {errors}")
        root = etree.fromstring(xml_bytes)
        party = root.find(f'.//{{*}}Accounting{role}Party/{{*}}Party')
        self.assertIsNotNone(party, f"No Accounting{role}Party/Party node in the XML")

        def pairs(xpath):
            return [(el.get('schemeID'), (el.text or '').strip()) for el in party.findall(xpath)]

        return {
            'endpoint': pairs('{*}EndpointID'),
            'identification': pairs('{*}PartyIdentification/{*}ID'),
            'legal_entity': pairs('{*}PartyLegalEntity/{*}CompanyID'),
            'tax_scheme': [
                (
                    (ts.findtext('{*}CompanyID') or '').strip(),
                    (ts.findtext('{*}TaxScheme/{*}ID') or '').strip(),
                )
                for ts in party.findall('{*}PartyTaxScheme')
            ],
        }

    def _assert_schematron_party(self, nodes, *, endpoint, legal_entity, tax_scheme, identification=None):
        """Assert the four nodes and the structural rules the EN16931/Peppol schematron enforces."""
        # [PEPPOL-EN16931-R010]/[R020]: a single electronic address with a registered EAS schemeID.
        self.assertEqual(nodes['endpoint'], [endpoint], "EndpointID mismatch")
        eas, value = endpoint
        registrable_eas = dict(self.env['res.partner']._fields['routing_scheme'].selection)
        self.assertIn(eas, registrable_eas, f"EndpointID schemeID {eas!r} is not a registered EAS")
        self.assertTrue(value, "EndpointID value must not be empty")
        # BT-30/BT-47: exactly one PartyLegalEntity/CompanyID.
        self.assertEqual(nodes['legal_entity'], [legal_entity], "PartyLegalEntity/CompanyID mismatch")
        self.assertTrue((legal_entity[1] or '').strip(), "PartyLegalEntity/CompanyID value must not be empty")
        # BT-31/BT-48: PartyTaxScheme/CompanyID (+ TaxScheme/ID).
        self.assertEqual(nodes['tax_scheme'], tax_scheme, "PartyTaxScheme mismatch")
        # BT-29/BT-46: PartyIdentification is optional; assert exact (absent by default).
        self.assertEqual(nodes['identification'], identification or [], "PartyIdentification mismatch")

    def _make_customer(self, country_xmlid, **values):
        return self.env['res.partner'].create({
            **self._create_partner_default_values(),
            'name': f"partner_{country_xmlid.split('.')[-1]}",
            'street': "Main Street 1",
            'zip': "0001",
            'city': "Capital",
            'country_id': self.env.ref(country_xmlid).id,
            **values,
        })

    # -------------------------------------------------------------------------
    # CUSTOMER PARTY NODES — one assertion per special-cased country
    # -------------------------------------------------------------------------

    def test_party_nodes_be(self):
        # BE: BE_EN drives EndpointID + PartyIdentification + PartyLegalEntity (schemeID 0208); VAT in PartyTaxScheme.
        partner = self._make_customer(
            'base.be', vat='BE0477472701', additional_identifiers={'BE_EN': '0477472701'},
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('0208', '0477472701'),
            identification=[('0208', '0477472701')],
            legal_entity=('0208', '0477472701'),
            tax_scheme=[('BE0477472701', 'VAT')],
        )

    def test_party_nodes_nl_kvk(self):
        # NL: KvK number drives PartyLegalEntity with schemeID 0106; VAT in PartyTaxScheme.
        partner = self._make_customer(
            'base.nl', vat='NL123456782B90', additional_identifiers={'NL_KVK': '12345678'},
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('0106', '12345678'),
            legal_entity=('0106', '12345678'),
            tax_scheme=[('NL123456782B90', 'VAT')],
        )

    def test_party_nodes_nl_oin(self):
        # NL: OIN is preferred over KvK/VAT in PartyLegalEntity with schemeID 0190.
        partner = self._make_customer(
            'base.nl', vat='NL123456782B90',
            additional_identifiers={'NL_OIN': '00000003123456780000'},
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('0190', '00000003123456780000'),
            legal_entity=('0190', '00000003123456780000'),
            tax_scheme=[('NL123456782B90', 'VAT')],
        )

    def test_party_nodes_se(self):
        # SE: organisationsnummer (digits only, no schemeID) in PartyLegalEntity; VAT in PartyTaxScheme.
        partner = self._make_customer(
            'base.se', vat='SE123456789701', additional_identifiers={'SE_EN': '1234567897'},
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('0007', '1234567897'),
            legal_entity=('0007', '1234567897'),
            tax_scheme=[('SE123456789701', 'VAT')],
        )

    def test_party_nodes_dk(self):
        # DK: CVR drives PartyLegalEntity with schemeID 0184; VAT in PartyTaxScheme; no ref fallback (DK-R-013).
        partner = self._make_customer(
            'base.dk', vat='DK58403288', additional_identifiers={'DK_CVR': '58403288'},
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('0184', '58403288'),
            legal_entity=('0184', '58403288'),
            tax_scheme=[('DK58403288', 'VAT')],
        )

    def test_party_nodes_lu(self):
        # LU: VAT preferred (carries the country prefix) in PartyLegalEntity with no schemeID.
        partner = self._make_customer(
            'base.lu', vat='LU12345613', routing_identifier='9938:12345613',
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('9938', '12345613'),
            legal_entity=(None, 'LU12345613'),
            tax_scheme=[('LU12345613', 'VAT')],
        )

    def test_party_nodes_hu(self):
        # HU: PartyTaxScheme/CompanyID is forced to carry the HU country prefix.
        partner = self._make_customer(
            'base.hu', vat='HU12345676', routing_identifier='9910:12345676',
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('9910', '12345676'),
            legal_entity=(None, 'HU12345676'),
            tax_scheme=[('HU12345676', 'VAT')],
        )

    def test_party_nodes_generic_vat_de(self):
        # Generic VAT country (DE): VAT in both PartyLegalEntity (no schemeID) and PartyTaxScheme.
        partner = self._make_customer(
            'base.de', vat='DE123456788', routing_identifier='9930:DE123456788',
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('9930', 'DE123456788'),
            legal_entity=(None, 'DE123456788'),
            tax_scheme=[('DE123456788', 'VAT')],
        )

    def test_party_nodes_generic_vat_it(self):
        # Generic VAT country (IT): VAT in both PartyLegalEntity (no schemeID) and PartyTaxScheme.
        partner = self._make_customer(
            'base.it', vat='IT12345670017', routing_identifier='0211:12345670017',
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('0211', '12345670017'),
            legal_entity=('0211', 'IT12345670017'),
            tax_scheme=[('IT12345670017', 'VAT')],
        )

    def test_party_nodes_gst_au(self):
        # AU: GST country — PartyTaxScheme/TaxScheme/ID must be GST (not VAT).
        partner = self._make_customer(
            'base.au', vat='53 930 548 027', routing_identifier='0151:53930548027',
        )
        nodes = self._generate_party_nodes(partner)
        self.assertEqual(nodes['endpoint'], [('0151', '53930548027')])
        # GST country: TaxScheme/ID must be GST (not VAT); the ABN is stored space-stripped.
        self.assertEqual(nodes['tax_scheme'], [('53930548027', 'GST')])

    def test_party_nodes_ref_fallback(self):
        # No typed identifier: PartyIdentification falls back to the partner reference (non-DK).
        partner = self._make_customer(
            'base.de', vat='DE123456788', ref='CUST-REF-42',
            routing_identifier='9930:DE123456788',
        )
        self._assert_schematron_party(
            self._generate_party_nodes(partner),
            endpoint=('9930', 'DE123456788'),
            identification=[(None, 'CUST-REF-42')],
            legal_entity=(None, 'DE123456788'),
            tax_scheme=[('DE123456788', 'VAT')],
        )

    # -------------------------------------------------------------------------
    # SUPPLIER PARTY NODES — Norway / Sweden
    # -------------------------------------------------------------------------

    # (Norway supplier nodes are already covered by test_ubl_export_bis3_no.)

    def test_supplier_party_nodes_se(self):
        # SE supplier: "GODKÄND FÖR F-SKATT" marker + digits-only org.nr in PartyLegalEntity.
        self.env.company.partner_id.write({
            'routing_identifier': False,
            'vat': 'SE123456789701',
            'additional_identifiers': {'SE_EN': '1234567897'},
            'country_id': self.env.ref('base.se').id,
        })
        nodes = self._generate_party_nodes(self.partner_be, role='Supplier')
        self.assertIn(('GODKÄND FÖR F-SKATT', 'TAX'), nodes['tax_scheme'])
        self.assertEqual(nodes['endpoint'], [('0007', '1234567897')])
        self.assertEqual(nodes['legal_entity'], [('0007', '1234567897')])
