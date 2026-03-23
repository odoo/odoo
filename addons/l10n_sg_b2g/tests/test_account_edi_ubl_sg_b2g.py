from datetime import datetime

from freezegun import freeze_time
from lxml import etree

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

NAMESPACES = {
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSgB2GEdiXml(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sg')
    def setUpClass(cls):
        super().setUpClass()

        cls.fakenow = datetime(2026, 6, 26, 10, 0, 0)
        cls.startClassPatcher(freeze_time(cls.fakenow))

        cls.company_data['company'].write({
            'vat': '197401143C',
            'l10n_sg_unique_entity_number': '00192200M',
            'street': 'Tyersall Avenue',
            'zip': '248048',
            'city': 'Central Singapore',
        })
        cls.company_data['company'].partner_id.write({
            'ref': 'VND001',
            'email': 'vendor@example.com',
        })

        cls.sg_customer = cls.env.ref('l10n_sg_b2g.l10n_sg_statutory_board_res_partner_acr')
        cls.sg_customer.write({
            'country_id': cls.env.ref('base.sg').id,
            'invoice_edi_format': 'ubl_sg_b2g',
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
        })

        cls.subbusiness_unit = cls.env.ref('l10n_sg_b2g.l10n_sg_statutory_board_res_partner_acr_acr01')

        cls.tax_sr = cls.env['account.tax'].search([
            ('company_id', '=', cls.company_data['company'].id),
            ('ubl_cii_tax_category_code', '=', 'SR'),
            ('type_tax_use', '=', 'sale'),
        ], limit=1)

        cls.tax_srca = cls.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', cls.company_data['company'].id),
            ('ubl_cii_tax_category_code', '=', 'SRCA-S'),
            ('type_tax_use', '=', 'sale'),
        ], limit=1)
        cls.tax_srca.active = True

        cls.b2g = cls.env['account.edi.xml.sg_b2g']

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _create_b2g_invoice(self, **kwargs):
        """Create a valid B2G invoice with sensible defaults, overridable via kwargs."""
        defaults = {
            'move_type': 'out_invoice',
            'partner_id': self.sg_customer,
            'invoice_date': fields.Date.today(),
            'l10n_sg_statutory_board_subbusiness_unit': self.subbusiness_unit,
            'narration': 'Invoice description for B2G',
            'invoice_line_ids': [
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    tax_ids=[Command.set(self.tax_sr.ids)],
                    price_unit=100.0,
                    name='Consulting services',
                ),
            ],
            'post': True,
        }
        defaults.update(kwargs)
        return self._create_invoice(**defaults)

    def _export(self, invoice):
        """Return (xml_bytes, errors_set) for the invoice."""
        return self.b2g._export_invoice(invoice)

    def _export_xml(self, invoice):
        """Return parsed lxml tree for the exported invoice."""
        xml_bytes, _ = self._export(invoice)
        return etree.fromstring(xml_bytes)

    def _get_constraints(self, invoice):
        """Return the set of constraint error strings for the invoice."""
        _, errors = self._export(invoice)
        return errors

    def _xpath(self, tree, path):
        return tree.xpath(path, namespaces=NAMESPACES)

    # -------------------------------------------------------------------------
    # Constraint: Business Unit
    # -------------------------------------------------------------------------

    def test_constraint_business_unit_required(self):
        """Missing sub-business unit produces the expected error."""
        invoice = self._create_b2g_invoice(l10n_sg_statutory_board_subbusiness_unit=None)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("You must specify a sub-business unit of Singaporean ministry / statutory board on the invoice."),
            errors,
        )

    # -------------------------------------------------------------------------
    # Constraint: Attention To (partner name)
    # -------------------------------------------------------------------------

    def test_constraint_attention_to_too_long(self):
        """Partner name longer than 20 characters triggers the char limit error."""
        long_name_partner = self.sg_customer.copy({'name': 'A' * 21})
        invoice = self._create_b2g_invoice(partner_id=long_name_partner)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("The partner name must be less than 20 characters."),
            errors,
        )

    def test_constraint_attention_to_invalid_char(self):
        """Partner name with non-ASCII characters triggers the invalid char error."""
        non_ascii_partner = self.sg_customer.copy({'name': 'Agençy'})  # ç is 0xE7
        invoice = self._create_b2g_invoice(partner_id=non_ascii_partner)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("The partner name must contain only acceptable characters (ASCII codes 32-127)."),
            errors,
        )

    def test_constraint_attention_to_exactly_20_chars(self):
        """Partner name of exactly 20 characters does not trigger the char limit error."""
        ok_partner = self.sg_customer.copy({'name': 'A' * 20})
        invoice = self._create_b2g_invoice(partner_id=ok_partner)
        _, errors = self._export(invoice)
        self.assertNotIn(
            self.env._("The partner name must be less than 20 characters."),
            errors,
        )

    # -------------------------------------------------------------------------
    # Constraint: Invoice Date
    # -------------------------------------------------------------------------

    def test_constraint_invoice_date_too_old(self):
        """Invoice dated more than 7 days ago triggers the date range error."""
        old_date = fields.Date.subtract(fields.Date.today(), days=8)
        invoice = self._create_b2g_invoice(invoice_date=old_date)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("The invoice date cannot be backdated by more than 7 calendar days or forward-dated."),
            errors,
        )

    def test_constraint_invoice_date_exactly_7_days_ago(self):
        """Invoice dated exactly 7 days ago is still valid."""
        seven_days_ago = fields.Date.subtract(fields.Date.today(), days=7)
        invoice = self._create_b2g_invoice(invoice_date=seven_days_ago)
        _, errors = self._export(invoice)
        self.assertNotIn(
            self.env._("The invoice date cannot be backdated by more than 7 calendar days or forward-dated."),
            errors,
        )

    def test_constraint_invoice_date_future(self):
        """Forward-dated invoice triggers the date range error."""
        tomorrow = fields.Date.add(fields.Date.today(), days=1)
        invoice = self._create_b2g_invoice(invoice_date=tomorrow)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("The invoice date cannot be backdated by more than 7 calendar days or forward-dated."),
            errors,
        )

    # -------------------------------------------------------------------------
    # Constraint: Vendor ID
    # -------------------------------------------------------------------------

    def test_constraint_vendor_id_required(self):
        """Missing Vendor ID (partner ref) on the company contact triggers the error."""
        self.company_data['company'].partner_id.ref = False
        invoice = self._create_b2g_invoice()
        try:
            _, errors = self._export(invoice)
            self.assertIn(
                self.env._(
                    "You must specify a vendor ID based on the vendor record created at Vendors@Gov on"
                    " the company contact's 'Reference' field."
                ),
                errors,
            )
        finally:
            self.company_data['company'].partner_id.ref = 'VND001'

    # -------------------------------------------------------------------------
    # Constraint: Email Address
    # -------------------------------------------------------------------------

    def test_constraint_email_required(self):
        """Missing email on the company contact triggers the error."""
        self.company_data['company'].partner_id.email = False
        invoice = self._create_b2g_invoice()
        try:
            _, errors = self._export(invoice)
            self.assertIn(
                self.env._("You must specify an email address on the company contact: %s", self.env.company.partner_id.name),
                errors,
            )
        finally:
            self.company_data['company'].partner_id.email = 'vendor@example.com'

    # -------------------------------------------------------------------------
    # Constraint: Invoice Description (narration / Terms and Conditions)
    # -------------------------------------------------------------------------

    def test_constraint_invoice_description_required(self):
        """Missing narration triggers the description required error."""
        invoice = self._create_b2g_invoice(narration=False)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("You must specify an invoice description on 'Terms and Conditions' field."),
            errors,
        )

    def test_constraint_invoice_description_too_long(self):
        """Narration longer than 254 characters triggers the char limit error."""
        long_narration = 'A' * 255
        invoice = self._create_b2g_invoice(narration=long_narration)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("The invoice description on 'Terms and Conditions' field must be less than 254 characters."),
            errors,
        )

    def test_constraint_invoice_description_exactly_254_chars(self):
        """Narration of exactly 254 characters does not trigger the char limit error."""
        ok_narration = 'A' * 254
        invoice = self._create_b2g_invoice(narration=ok_narration)
        _, errors = self._export(invoice)
        self.assertNotIn(
            self.env._("The invoice description on 'Terms and Conditions' field must be less than 254 characters."),
            errors,
        )

    # -------------------------------------------------------------------------
    # Constraint: Related Invoice ID (credit notes)
    # -------------------------------------------------------------------------

    def test_constraint_related_invoice_id_required_for_credit_note(self):
        """Credit note without a customer reference triggers the related invoice error."""
        credit_note = self._create_invoice(
            move_type='out_refund',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Credit note description',
            ref=False,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    tax_ids=[Command.set(self.tax_sr.ids)],
                    price_unit=100.0,
                ),
            ],
            post=True,
        )
        _, errors = self._export(credit_note)
        self.assertIn(
            self.env._("You must specify a related invoice ID on 'Customer Reference' field."),
            errors,
        )

    def test_credit_note_with_ref_has_no_related_invoice_error(self):
        """Credit note with a customer reference (ref) does not trigger the error."""
        credit_note = self._create_invoice(
            move_type='out_refund',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Credit note description',
            ref='INV/2026/00001',
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    tax_ids=[Command.set(self.tax_sr.ids)],
                    price_unit=100.0,
                ),
            ],
            post=True,
        )
        _, errors = self._export(credit_note)
        self.assertNotIn(
            self.env._("You must specify a related invoice ID on 'Customer Reference' field."),
            errors,
        )

    # -------------------------------------------------------------------------
    # Constraint: Payment Terms Code
    # -------------------------------------------------------------------------

    def test_constraint_payment_term_code_required(self):
        """Payment term without a B2G code triggers the code required error."""
        payment_term = self.env['account.payment.term'].create({
            'name': 'Net 30 (no B2G code)',
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30})],
        })
        invoice = self._create_b2g_invoice(invoice_payment_term_id=payment_term)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("The payment term '%s' must have a B2G payment terms code configured.", payment_term.name),
            errors,
        )

    def test_constraint_payment_term_with_b2g_code_passes(self):
        """Payment term with a B2G code does not trigger the code error."""
        b2g_payment_term = self.env.ref('l10n_sg_b2g.l10n_sg_payment_term_30d')
        invoice = self._create_b2g_invoice(invoice_payment_term_id=b2g_payment_term)
        _, errors = self._export(invoice)
        self.assertNotIn(
            self.env._("The payment term '%s' must have a B2G payment terms code configured.", b2g_payment_term.name),
            errors,
        )

    # -------------------------------------------------------------------------
    # Constraint: Customer Accounting (mixed SR/SRCA)
    # -------------------------------------------------------------------------

    def test_constraint_customer_accounting_mixed_taxes(self):
        """Invoice with both standard-rated and customer-accounting lines triggers the error."""
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Invoice description',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=100.0),
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_srca.ids)], price_unit=100.0),
            ],
            post=True,
        )
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._(
                "Invoices for items subject to customer accounting (SRCA-S/SRCA-C) should be"
                " separately submitted from invoices for standard-rated and zero-rated items."
            ),
            errors,
        )

    def test_constraint_customer_accounting_only_srca_passes(self):
        """Invoice with only SRCA-S lines does not trigger the mixed accounting error."""
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Invoice description',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_srca.ids)], price_unit=100.0),
            ],
            post=True,
        )
        _, errors = self._export(invoice)
        self.assertNotIn(
            self.env._(
                "Invoices for items subject to customer accounting (SRCA-S/SRCA-C) should be"
                " separately submitted from invoices for standard-rated and zero-rated items."
            ),
            errors,
        )

    # -------------------------------------------------------------------------
    # Constraint: Invoice Line Number (max 5 chars)
    # -------------------------------------------------------------------------

    def test_constraint_invoice_line_number_too_long(self):
        """Invoice line with a custom line number > 5 characters triggers the error."""
        invoice = self._create_b2g_invoice()
        invoice.invoice_line_ids.l10n_sg_b2g_invoice_line_no = 'LINE6'
        self.env.flush_all()
        # Repost or re-export
        _, errors = self._export(invoice)
        self.assertNotIn(
            self.env._("The invoice line number must be less than 5 characters."),
            errors,
        )

    def test_constraint_invoice_line_number_too_long_6_chars(self):
        """Invoice line with a 6-character custom line number triggers the error."""
        invoice = self._create_b2g_invoice()
        invoice.invoice_line_ids[0].l10n_sg_b2g_invoice_line_no = '123456'
        self.env.flush_all()
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._("The invoice line number must be less than 5 characters."),
            errors,
        )

    # -------------------------------------------------------------------------
    # Constraint: Payee Party (remit-to different from supplier)
    # -------------------------------------------------------------------------

    def test_constraint_payee_vendor_id_required(self):
        """PayeeParty without a vendor ID (ref) triggers the error."""
        other_partner = self.env['res.partner'].create({
            'name': 'Bank Holder',
            'ref': False,
            'company_id': False,
        })
        bank_account = self.env['res.partner.bank'].create({
            'account_number': 'SG001234567',
            'partner_id': other_partner.id,
            'company_id': self.company_data['company'].id,
            'allow_out_payment': True,
        })
        invoice = self._create_b2g_invoice(partner_bank_id=bank_account)
        _, errors = self._export(invoice)
        self.assertIn(
            self.env._(
                "You must specify a vendor ID based on the vendor record created at Vendors@Gov on"
                " the bank account holder contact's 'Reference' field."
            ),
            errors,
        )

    # -------------------------------------------------------------------------
    # XML Structure: BuyerReference (sub-business unit code)
    # -------------------------------------------------------------------------

    def test_buyer_reference_uses_business_unit_code(self):
        """BuyerReference in the UBL XML is populated with the sub-business unit code."""
        invoice = self._create_b2g_invoice()
        tree = self._export_xml(invoice)
        buyer_refs = self._xpath(tree, '//cbc:BuyerReference')
        self.assertEqual(len(buyer_refs), 1)
        self.assertEqual(buyer_refs[0].text, self.subbusiness_unit.code)

    # -------------------------------------------------------------------------
    # XML Structure: BillingReference for credit notes
    # -------------------------------------------------------------------------

    def test_credit_note_has_billing_reference_with_original_invoice_id(self):
        """Credit note XML includes BillingReference pointing to the original invoice ref."""
        credit_note = self._create_invoice(
            move_type='out_refund',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Credit note',
            ref='INV/2026/00001',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=100.0),
            ],
            post=True,
        )
        tree = self._export_xml(credit_note)
        billing_ref_ids = self._xpath(tree, '//cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID')
        self.assertEqual(len(billing_ref_ids), 1)
        self.assertEqual(billing_ref_ids[0].text, 'INV/2026/00001')

    # -------------------------------------------------------------------------
    # XML Structure: OrderReference (only when from PO/II)
    # -------------------------------------------------------------------------

    def test_invoice_without_po_has_no_order_reference(self):
        """Standard invoice (not from PO) does not include an OrderReference node."""
        invoice = self._create_b2g_invoice()
        self.assertFalse(invoice.l10n_sg_is_from_po_invoice)
        tree = self._export_xml(invoice)
        order_refs = self._xpath(tree, '//cac:OrderReference')
        self.assertEqual(len(order_refs), 0)

    # -------------------------------------------------------------------------
    # XML Structure: Party Name uses partner.name (not display_name)
    # -------------------------------------------------------------------------

    def test_party_name_uses_partner_name_not_display_name(self):
        """
        Customer party name in XML is partner.name, not partner.display_name.
        This matters when the customer has child contacts whose display_name differs.
        """
        contact = self.env['res.partner'].create({
            'name': 'AttnContact',
            'parent_id': self.sg_customer.id,
            'type': 'contact',
            'company_id': False,
        })
        invoice = self._create_b2g_invoice(partner_id=contact)
        tree = self._export_xml(invoice)
        party_names = self._xpath(tree, '//cac:AccountingCustomerParty//cac:PartyName/cbc:Name')
        self.assertTrue(party_names)
        # partner.name is 'AttnContact', display_name might be 'GovAgency, AttnContact'
        self.assertEqual(party_names[0].text, 'AttnContact')

    # -------------------------------------------------------------------------
    # XML Structure: PaymentTerms with B2G code
    # -------------------------------------------------------------------------

    def test_payment_terms_node_includes_b2g_code(self):
        """PaymentTerms Note in XML is set to the B2G payment term code."""
        b2g_payment_term = self.env.ref('l10n_sg_b2g.l10n_sg_payment_term_30d')
        invoice = self._create_b2g_invoice(invoice_payment_term_id=b2g_payment_term)
        tree = self._export_xml(invoice)
        payment_terms_notes = self._xpath(tree, '//cac:PaymentTerms/cbc:Note')
        self.assertTrue(payment_terms_notes)
        self.assertEqual(payment_terms_notes[0].text, b2g_payment_term.l10n_sg_b2g_code)

    def test_no_payment_terms_node_when_no_payment_term(self):
        """No PaymentTerms node is generated when the invoice has no payment term."""
        invoice = self._create_b2g_invoice(invoice_payment_term_id=False)
        tree = self._export_xml(invoice)
        payment_terms = self._xpath(tree, '//cac:PaymentTerms')
        # PaymentTerms from the B2G model should be absent; BIS3 may add its own
        # for early payment discounts, but for a plain invoice without terms there should be none.
        b2g_notes = [pt for pt in payment_terms if any(n.text for n in pt.xpath('cbc:Note', namespaces=NAMESPACES))]
        self.assertFalse(b2g_notes)

    # -------------------------------------------------------------------------
    # XML Structure: Freight charge as document-level AllowanceCharge
    # -------------------------------------------------------------------------

    def test_freight_charge_generates_allowance_charge_node(self):
        """
        A line using the freight charge product is rendered as a document-level
        AllowanceCharge (FC reason code) instead of an invoice line.
        """
        freight_product = self.env.ref('l10n_sg_b2g.product_product_sg_b2g_freight_charge')
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Invoice with freight',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=100.0),
                self._prepare_invoice_line(product_id=freight_product, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=50.0),
            ],
            post=True,
        )
        tree = self._export_xml(invoice)
        allowance_charges = self._xpath(tree, '//cac:AllowanceCharge')
        reason_codes = [ac.findtext('cbc:AllowanceChargeReasonCode', namespaces=NAMESPACES) for ac in allowance_charges]
        self.assertIn('FC', reason_codes)

    def test_freight_charge_has_charge_indicator_true(self):
        """Freight charge with positive amount has ChargeIndicator set to 'true'."""
        freight_product = self.env.ref('l10n_sg_b2g.product_product_sg_b2g_freight_charge')
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Invoice with freight',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=100.0),
                self._prepare_invoice_line(product_id=freight_product, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=50.0),
            ],
            post=True,
        )
        tree = self._export_xml(invoice)
        freight_acs = [
            ac for ac in self._xpath(tree, '//cac:AllowanceCharge')
            if ac.findtext('cbc:AllowanceChargeReasonCode', namespaces=NAMESPACES) == 'FC'
        ]
        self.assertTrue(freight_acs)
        self.assertEqual(freight_acs[0].findtext('cbc:ChargeIndicator', namespaces=NAMESPACES), 'true')

    def test_freight_charge_adjusts_tax_exclusive_amount(self):
        """
        Freight charge (50 SGD, 9% GST) raises TaxExclusiveAmount and
        TaxInclusiveAmount in LegalMonetaryTotal relative to line-only totals.
        """
        freight_product = self.env.ref('l10n_sg_b2g.product_product_sg_b2g_freight_charge')
        base_invoice = self._create_b2g_invoice()
        base_tree = self._export_xml(base_invoice)
        base_excl = float(self._xpath(base_tree, '//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount')[0].text)

        invoice_with_freight = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Invoice with freight',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=100.0),
                self._prepare_invoice_line(product_id=freight_product, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=50.0),
            ],
            post=True,
        )
        freight_tree = self._export_xml(invoice_with_freight)
        freight_excl = float(self._xpath(freight_tree, '//cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount')[0].text)

        self.assertAlmostEqual(freight_excl - base_excl, 50.0, places=2)

    # -------------------------------------------------------------------------
    # XML Structure: OrderLineReference on invoice lines
    # -------------------------------------------------------------------------

    def test_invoice_line_has_order_line_reference(self):
        """Every invoice line has an OrderLineReference/LineID node."""
        invoice = self._create_b2g_invoice()
        tree = self._export_xml(invoice)
        line_ids = self._xpath(tree, '//cac:InvoiceLine/cac:OrderLineReference/cbc:LineID')
        self.assertTrue(line_ids, "Expected at least one OrderLineReference/LineID")

    def test_custom_invoice_line_number_used_in_order_line_reference(self):
        """Custom l10n_sg_b2g_invoice_line_no is reflected in OrderLineReference/LineID."""
        invoice = self._create_b2g_invoice()
        invoice.invoice_line_ids[0].l10n_sg_b2g_invoice_line_no = 'PO01'
        self.env.flush_all()
        tree = self._export_xml(invoice)
        line_ids = self._xpath(tree, '//cac:InvoiceLine/cac:OrderLineReference/cbc:LineID')
        self.assertTrue(any(n.text == 'PO01' for n in line_ids))

    # -------------------------------------------------------------------------
    # XML Structure: PayeeParty when bank account holder differs from supplier
    # -------------------------------------------------------------------------

    def test_payee_party_added_when_different_from_supplier(self):
        """
        When the bank account's partner differs from the company's commercial partner,
        a PayeeParty node with PartyIdentification and PartyName is generated.
        """
        other_partner = self.env['res.partner'].create({
            'name': 'Payment Holder',
            'ref': 'VND002',
            'company_id': False,
        })
        bank_account = self.env['res.partner.bank'].create({
            'account_number': 'SG009876543',
            'partner_id': other_partner.id,
            'company_id': self.company_data['company'].id,
            'allow_out_payment': True,
        })
        invoice = self._create_b2g_invoice(partner_bank_id=bank_account)
        tree = self._export_xml(invoice)
        payee_id = self._xpath(tree, '//cac:PayeeParty/cac:PartyIdentification/cbc:ID')
        payee_name = self._xpath(tree, '//cac:PayeeParty/cac:PartyName/cbc:Name')
        self.assertTrue(payee_id)
        self.assertEqual(payee_id[0].text, 'VND002')
        self.assertTrue(payee_name)
        self.assertEqual(payee_name[0].text, 'Payment Holder')

    def test_no_payee_party_when_bank_holder_is_supplier(self):
        """
        When the bank account's partner is the same as the company's commercial partner,
        no PayeeParty node is generated.
        """
        company_partner = self.company_data['company'].partner_id
        bank_account = self.env['res.partner.bank'].create({
            'account_number': 'SG001111111',
            'partner_id': company_partner.id,
            'company_id': self.company_data['company'].id,
            'allow_out_payment': True,
        })
        invoice = self._create_b2g_invoice(partner_bank_id=bank_account)
        tree = self._export_xml(invoice)
        payee_party = self._xpath(tree, '//cac:PayeeParty')
        self.assertFalse(payee_party)

    # -------------------------------------------------------------------------
    # XML Structure: Credit note OrderLineReference
    # -------------------------------------------------------------------------

    def test_credit_note_line_has_order_line_reference(self):
        """Every credit note line has an OrderLineReference/LineID node."""
        credit_note = self._create_invoice(
            move_type='out_refund',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Credit note',
            ref='INV/2026/00001',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=100.0),
            ],
            post=True,
        )
        tree = self._export_xml(credit_note)
        line_ids = self._xpath(tree, '//cac:CreditNoteLine/cac:OrderLineReference/cbc:LineID')
        self.assertTrue(line_ids, "Expected at least one OrderLineReference/LineID on credit note lines")

    # -------------------------------------------------------------------------
    # Freight: _is_document_allowance_charge
    # -------------------------------------------------------------------------

    def test_freight_product_is_document_allowance_charge(self):
        """
        The freight charge product is classified as a document-level AllowanceCharge,
        meaning it does NOT appear as an invoice line in the XML.
        """
        freight_product = self.env.ref('l10n_sg_b2g.product_product_sg_b2g_freight_charge')
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.sg_customer,
            invoice_date=fields.Date.today(),
            l10n_sg_statutory_board_subbusiness_unit=self.subbusiness_unit,
            narration='Invoice with freight',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=100.0, name='Service A'),
                self._prepare_invoice_line(product_id=freight_product, tax_ids=[Command.set(self.tax_sr.ids)], price_unit=50.0),
            ],
            post=True,
        )
        tree = self._export_xml(invoice)
        invoice_lines = self._xpath(tree, '//cac:InvoiceLine')
        # Only 1 regular line; freight is at document level
        self.assertEqual(len(invoice_lines), 1)

    # -------------------------------------------------------------------------
    # Valid invoice: no B2G-specific errors
    # -------------------------------------------------------------------------

    def test_valid_invoice_has_no_b2g_errors(self):
        """A fully valid B2G invoice should produce no constraint errors."""
        invoice = self._create_b2g_invoice()
        _, errors = self._export(invoice)
        b2g_error_prefixes = (
            'You must specify a sub-business unit',
            'The partner name must be',
            'The invoice number must be',
            'The invoice date cannot',
            'You must specify a vendor ID',
            'You must specify an email address',
            'You must specify an Invoicing Instruction',
            'You must specify an invoice description',
            'You must specify a related invoice ID',
            'Invoices for items subject to customer accounting',
            'The payment term',
        )
        b2g_errors = [e for e in errors if any(e.startswith(p) for p in b2g_error_prefixes)]
        self.assertFalse(b2g_errors, f"Unexpected B2G errors on a valid invoice: {b2g_errors}")
