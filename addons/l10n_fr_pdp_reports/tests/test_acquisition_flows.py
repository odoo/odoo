from base64 import b64decode
from unittest.mock import patch

from lxml import etree

from odoo import fields
from odoo.tests.common import tagged

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpAcquisitionFlows(PdpTestCommon):
    def test_acquisition_report_document_uses_by_issuer_role(self):
        """Acquisition transaction payload must publish issuer role BY (TT-15)."""
        self._create_vendor_bill(partner=self.partner_international)
        flows = self._run_aggregation()
        purchase_flow = flows.filtered(lambda f: f.report_kind == 'transaction' and f.operation_type == 'purchase')[:1]
        self.assertTrue(purchase_flow, 'Acquisition flow should be created for international purchases')

        payload_xml = etree.fromstring(b64decode(purchase_flow.payload))
        self.assertEqual(payload_xml.findtext('./ReportDocument/Issuer/RoleCode'), 'BY')
        self.assertEqual(payload_xml.findtext('./ReportDocument/Sender/RoleCode'), 'WK')

    def test_international_purchase_creates_acquisition_flow(self):
        """International vendor bill must create a dedicated acquisition flow."""
        self._create_vendor_bill(partner=self.partner_international)
        flows = self._run_aggregation()
        purchase_flow = flows.filtered(lambda f: f.report_kind == 'transaction' and f.operation_type == 'purchase')[:1]
        self.assertTrue(purchase_flow, 'Acquisition flow should be created for international purchases')
        payload_xml = etree.fromstring(b64decode(purchase_flow.payload))
        seller_id = payload_xml.findtext('.//Invoice/Seller/CompanyId')
        buyer_id = payload_xml.findtext('.//Invoice/Buyer/CompanyId')
        self.assertIn(self.partner_international.vat, seller_id, 'Supplier should be reported as Seller')
        self.assertEqual(buyer_id, self.company.siret[:9], 'Company should be reported as Buyer')

    def test_mixed_sales_purchases_creates_separate_flows(self):
        """Sales and purchases must create separate flows with correct TT-15 roles (SE vs BY)."""
        # Create DROM-COM partner (Guyane = e-reporting, international)
        country_gf = self.env['res.country'].search([('code', '=', 'GF')], limit=1)
        if not country_gf:
            country_gf = self.env['res.country'].create({
                'name': 'French Guiana',
                'code': 'GF',
            })
        partner_guyane = self.env['res.partner'].create({
            'name': 'Supplier Guyane',
            'country_id': country_gf.id,
            'vat': 'FR12345678901',
        })

        # Create B2C sale (France, no VAT)
        invoice_b2c = self._create_invoice(partner=self.partner_b2c)

        # Create B2BI sale (international)
        invoice_b2bi_sale = self._create_invoice(partner=self.partner_international)

        # Create B2BI purchase (international)
        bill_b2bi = self._create_vendor_bill(partner=self.partner_international)

        # Create DROM purchase (Guyane = international e-reporting)
        bill_drom = self._create_vendor_bill(partner=partner_guyane)

        # Run aggregation
        flows = self._run_aggregation()

        # Verify at least 2 flows created (sales SE + purchases BY)
        self.assertGreaterEqual(len(flows), 2, 'Should create at least 2 flows (sales + purchases)')

        # Filter by operation type
        flow_sale = flows.filtered(lambda f: f.operation_type == 'sale')
        flow_purchase = flows.filtered(lambda f: f.operation_type == 'purchase')

        self.assertTrue(flow_sale, 'Sale flow (SE) must exist')
        self.assertTrue(flow_purchase, 'Purchase flow (BY) must exist')

        # Verify sales are in sale flow
        self.assertIn(invoice_b2c, flow_sale.move_ids, 'B2C sale should be in sale flow')
        self.assertIn(invoice_b2bi_sale, flow_sale.move_ids, 'B2BI sale should be in sale flow')

        # Verify purchases are in purchase flow
        self.assertIn(bill_b2bi, flow_purchase.move_ids, 'International purchase should be in purchase flow')
        self.assertIn(bill_drom, flow_purchase.move_ids, 'DROM purchase should be in purchase flow')

        # Verify Guyane purchase is classified as international
        self.assertEqual(
            bill_drom._get_l10n_fr_pdp_transaction_type(),
            'international',
            'Guyane purchase should be classified as international (e-reporting)'
        )

    def test_drom_com_country_code_mapping_in_xml(self):
        """DROM-COM country codes must be mapped to FR in generated XML."""
        # Create DROM-COM partners for different territories
        country_gf = self.env['res.country'].search([('code', '=', 'GF')], limit=1)
        if not country_gf:
            country_gf = self.env['res.country'].create({
                'name': 'French Guiana',
                'code': 'GF',
            })

        country_gp = self.env['res.country'].search([('code', '=', 'GP')], limit=1)
        if not country_gp:
            country_gp = self.env['res.country'].create({
                'name': 'Guadeloupe',
                'code': 'GP',
            })

        partner_guyane = self.env['res.partner'].create({
            'name': 'Supplier Guyane',
            'country_id': country_gf.id,
            'vat': 'FR40303265045',  # Valid FR VAT
        })

        partner_guadeloupe = self.env['res.partner'].create({
            'name': 'Supplier Guadeloupe',
            'country_id': country_gp.id,
            'vat': 'FR23334175221',  # Valid FR VAT
        })

        # Create vendor bills from DROM-COM territories
        self._create_vendor_bill(partner=partner_guyane)
        self._create_vendor_bill(partner=partner_guadeloupe)

        # Run aggregation
        flows = self._run_aggregation()
        purchase_flow = flows.filtered(lambda f: f.operation_type == 'purchase')[:1]

        self.assertTrue(purchase_flow, 'Purchase flow should be created')

        # Parse XML payload
        payload_xml = etree.fromstring(b64decode(purchase_flow.payload))

        # Find all seller addresses in the XML
        seller_countries = payload_xml.xpath('.//Invoice/Seller/PostalAddress/CountryId/text()')

        # Verify all DROM-COM codes are mapped to FR
        for country_code in seller_countries:
            self.assertEqual(
                country_code,
                'FR',
                f'DROM-COM country code should be mapped to FR in XML, got {country_code}'
            )

    def test_no_payment_flow_for_autoliquidation(self):
        """Service B2BI with autoliquidation (reverse charge) should NOT create payment flow."""
        # Create tax for export (0% - autoliquidation)
        tax_group = self.env['account.tax.group'].search([
            ('country_id', '=', self.env.ref('base.fr').id)
        ], limit=1)
        if not tax_group:
            tax_group = self.env['account.tax.group'].create({
                'name': 'FR VAT',
                'country_id': self.env.ref('base.fr').id,
            })

        tax_export = self.env['account.tax'].create({
            'name': 'TVA 0% Export',
            'amount': 0.0,
            'type_tax_use': 'sale',
            'company_id': self.company.id,
            'tax_group_id': tax_group.id,
        })

        # Create service invoice to Germany with autoliquidation
        service_invoice = self._create_invoice(
            partner=self.partner_international,
            product=self.service_product,
            taxes=tax_export,
        )

        # Mark as sent and register payment
        service_invoice.is_move_sent = True
        self._create_payment_for_invoice(service_invoice)

        # Run aggregation
        flows = self._run_aggregation()

        # Verify transaction flow exists
        transaction_flow = flows.filtered(lambda f: f.report_kind == 'transaction' and f.operation_type == 'sale')
        self.assertTrue(transaction_flow, 'Transaction flow should exist for service')
        self.assertIn(service_invoice, transaction_flow.move_ids, 'Service invoice should be in transaction flow')

        # Verify NO payment flow for autoliquidation
        payment_flows = flows.filtered(lambda f: f.report_kind == 'payment' and f.operation_type == 'sale')
        if payment_flows:
            self.assertNotIn(
                service_invoice,
                payment_flows.move_ids,
                'Service with autoliquidation should NOT be in payment flow'
            )

    def test_payment_flow_for_french_vat_on_foreign_client(self):
        """Special case: French VAT collected on foreign client should create payment flow (bloc 10.2)."""
        # Create service invoice to Germany with French VAT (special case)
        # Using the default tax_20 which is French VAT
        service_invoice = self._create_invoice(
            partner=self.partner_international,
            product=self.service_product,
            taxes=self.tax_20,
        )

        # Mark as sent and register payment
        service_invoice.is_move_sent = True
        self._create_payment_for_invoice(service_invoice)

        # Run aggregation
        flows = self._run_aggregation()

        # Verify payment flow exists for French VAT on foreign client
        payment_flow = flows.filtered(lambda f: f.report_kind == 'payment' and f.operation_type == 'sale')[:1]
        self.assertTrue(payment_flow, 'Payment flow should exist when French VAT collected on foreign client')
        self.assertIn(service_invoice, payment_flow.move_ids, 'Service invoice should be in payment flow')

        # Verify XML contains bloc 10.2 (InvoicePayment)
        payload_xml = etree.fromstring(b64decode(payment_flow.payload))
        invoices = payload_xml.findall('.//Invoice')
        self.assertGreater(len(invoices), 0, 'Payment flow XML should contain Invoice elements (bloc 10.2)')

    def test_international_vendor_bill_gets_reporting_status(self):
        """International vendor bills should expose a PDP status like sale invoices."""
        bill = self._create_vendor_bill(partner=self.partner_international)
        self._run_aggregation()
        bill.invalidate_recordset(['l10n_fr_pdp_status'])
        self.assertEqual(
            bill.l10n_fr_pdp_status,
            'ready',
            'International posted vendor bill should be ready once flow payload is built',
        )

    def test_domestic_vendor_bill_stays_out_of_scope(self):
        """Domestic FR vendor bills should stay out of scope for Flux 10 acquisitions."""
        partner_domestic = self.env['res.partner'].create({
            'name': 'Domestic Supplier',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
            'property_account_receivable_id': self.partner_b2c.property_account_receivable_id.id,
            'property_account_payable_id': self.partner_b2c.property_account_payable_id.id,
        })
        bill = self._create_vendor_bill(partner=partner_domestic)
        self._run_aggregation()
        bill.invalidate_recordset(['l10n_fr_pdp_status'])
        self.assertEqual(
            bill.l10n_fr_pdp_status,
            'out_of_scope',
            'Domestic vendor bill should be out of scope for PDP reporting',
        )

    def test_invalid_international_bill_turns_error_in_grace(self):
        """Invalid acquisition bill stays pending in open period, then turns error in grace."""
        partner_no_vat = self.env['res.partner'].create({
            'name': 'International Supplier Missing VAT',
            'country_id': self.env.ref('base.be').id,
            'property_account_receivable_id': self.partner_b2c.property_account_receivable_id.id,
            'property_account_payable_id': self.partner_b2c.property_account_payable_id.id,
        })
        bill = self._create_vendor_bill(partner=partner_no_vat)

        open_day = fields.Date.from_string('2025-02-07')   # within decade 1-10
        grace_day = fields.Date.from_string('2025-02-15')  # after period end 10th

        with patch('odoo.fields.Date.context_today', return_value=open_day):
            self._run_aggregation()
            bill.invalidate_recordset(['l10n_fr_pdp_status'])
            self.assertEqual(
                bill.l10n_fr_pdp_status,
                'pending',
                'Invalid acquisition bill must stay pending during open period',
            )

        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            self._aggregate_company()
            flow = bill.l10n_fr_pdp_flow_ids.filtered(lambda f: f.operation_type == 'purchase')[:1]
            self.assertTrue(flow, 'Acquisition flow should still reference the bill in grace period')
            flow._build_payload()
            bill.invalidate_recordset(['l10n_fr_pdp_status'])
            self.assertEqual(
                bill.l10n_fr_pdp_status,
                'error',
                'Invalid acquisition bill must surface as error during grace period',
            )
