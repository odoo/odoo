import base64
import re
from unittest.mock import patch

from lxml import etree

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.l10n_fr_pdp_reports.models.pdp_payload import PdpPayloadBuilder

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpValidationAndPayload(PdpTestCommon):
    def test_report_document_header_contains_expected_fields(self):
        """Root ReportDocument should expose required Flux 10 header fields."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))

        report_document = payload_xml.find('./ReportDocument')
        self.assertIsNotNone(report_document, 'ReportDocument block should be present')
        self.assertEqual(report_document.findtext('Id'), flow.tracking_id)
        self.assertTrue(report_document.findtext('Name'))
        issue_datetime = report_document.findtext('IssueDateTime/DateTimeString')
        self.assertRegex(issue_datetime or '', r'^\d{14}$')
        self.assertIn(report_document.findtext('TypeCode'), {'IN', 'RE'})

        sender = report_document.find('./Sender')
        self.assertIsNotNone(sender)
        sender_id = sender.find('./Id')
        self.assertIsNotNone(sender_id)
        self.assertEqual(sender_id.get('schemeId'), '0238')
        self.assertTrue(sender.findtext('Name'))
        self.assertEqual(sender.findtext('RoleCode'), 'WK')
        sender_uri = sender.findtext('URIUniversalCommunication/URIID')
        if sender_uri is not None:
            self.assertTrue(sender_uri)

        issuer = report_document.find('./Issuer')
        self.assertIsNotNone(issuer)
        issuer_id = issuer.find('./Id')
        self.assertIsNotNone(issuer_id)
        self.assertEqual(issuer_id.get('schemeId'), '0002')
        self.assertTrue(re.fullmatch(r'\d{9}', issuer_id.text or ''))
        self.assertEqual(issuer.findtext('RoleCode'), 'SE')
        issuer_uri = issuer.findtext('URIUniversalCommunication/URIID')
        if issuer_uri is not None:
            self.assertTrue(issuer_uri)

    def test_company_identifier_validation_errors(self):
        """Missing company SIRET/VAT should block payload build with a clear error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.company.write({'siret': False})
        self.company.partner_id.write({'vat': False})

        with self.assertRaises(UserError) as ctx:
            flow._build_payload()
        message = str(ctx.exception)
        self.assertIn('missing its SIRET', message)
        self.assertIn('missing its VAT number', message)

    def test_tt122_fiscal_representative_when_seller_vat_missing_on_exempt_invoice(self):
        """When seller VAT is missing on category E, TT-122 representative VAT must be used."""
        exempt_tax = self.tax_20.copy({
            'name': 'TT122 Exempt Tax',
            'amount': 0.0,
            'l10n_fr_pdp_vatex_code': 'VATEX-EU-IC',
        })
        self._create_invoice(partner=self.partner_international, sent=True, taxes=exempt_tax)
        representative_vat = self.company.partner_id.vat
        self.assertTrue(representative_vat, 'Company partner VAT should exist for this test setup')
        self.company.partner_id.write({'vat': False})
        self.company.write({'l10n_fr_pdp_fiscal_representative_vat': representative_vat})

        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        representative_vat_xml = payload_xml.findtext('.//Invoice/SellerTaxRepresentative/TaxRegistrationId')
        self.assertEqual(representative_vat_xml, representative_vat)

    def test_invalid_identifier_and_due_code_block_payload(self):
        """Invalid TT-1 identifier and invalid TT-64 code must raise validation errors."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._is_valid_transmission_identifier', return_value=False):
            with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._is_valid_due_date_code', return_value=False):
                with self.assertRaises(UserError) as ctx:
                    flow._build_payload()
        message = str(ctx.exception)
        self.assertIn('TT-1', message)
        self.assertIn('tax due date type code', message)

    def test_transmission_identifier_accepts_spec_characters(self):
        """TT-1 should accept documented characters (space, -, +, _, /)."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        builder = PdpPayloadBuilder(flow)
        self.assertTrue(builder._is_valid_transmission_identifier('AB 12-3_4+/X'))
        self.assertFalse(builder._is_valid_transmission_identifier(' AB12'))
        self.assertFalse(builder._is_valid_transmission_identifier('AB  12'))
        self.assertFalse(builder._is_valid_transmission_identifier('AB*12'))

    def test_invalid_tt19_invoice_identifier_blocks_payload(self):
        """TT-19 should reject unsupported characters/length."""
        invoice = self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        invoice.write({'l10n_fr_pdp_invoice_reference': 'INV*INVALID'})
        with self.assertRaises(UserError) as ctx:
            flow._build_payload()
        self.assertIn('TT-19', str(ctx.exception))

    def test_invalid_tt21_invoice_type_code_blocks_payload(self):
        """TT-21 should reject unsupported type codes."""
        invoice = self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        invoice.write({'l10n_fr_pdp_bt3_code': '999'})
        with self.assertRaises(UserError) as ctx:
            flow._build_payload()
        self.assertIn('TT-21', str(ctx.exception))

    def test_tt21_386_500_incompatible_with_b4_s4_m4(self):
        """G1.60 should reject frame B4/S4/M4 when TT-21 is 386 or 500."""
        invoice = self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        invoice.write({'l10n_fr_pdp_bt3_code': '386'})
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._get_cadre_code', return_value='B4'):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('G1.60', str(ctx.exception))

    def test_duplicate_invoice_identity_blocks_payload(self):
        """G1.42 should reject duplicate 10.1 identity within same transmission."""
        invoice_1 = self._create_invoice(partner=self.partner_international, sent=True)
        invoice_2 = self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        builder = PdpPayloadBuilder(flow)
        invoice_vals_1 = builder._invoice_vals(invoice_1)
        invoice_vals_2 = builder._invoice_vals(invoice_2)
        invoice_vals_1['id'] = 'DUP-INV-001'
        invoice_vals_2['id'] = 'DUP-INV-001'
        invoice_vals_2['issue_date'] = invoice_vals_1['issue_date']
        invoice_vals_2['seller']['company_id'] = invoice_vals_1['seller']['company_id']

        errors = []
        builder._validate_invoices(
            {'invoices': [invoice_vals_1, invoice_vals_2], 'expected_international_invoices': True},
            flow.currency_id,
            errors,
        )
        self.assertTrue(any('G1.42' in err for err in errors), 'Duplicate identity should raise G1.42')

    def test_vatex_fr_cnwvat_allowed_only_on_credit_notes(self):
        """VATEX-FR-CNWVAT should be rejected on non-credit invoice types."""
        special_tax = self.tax_20.copy({
            'name': 'CNWVAT Tax',
            'amount': 0.0,
            'l10n_fr_pdp_vatex_code': 'VATEX-FR-CNWVAT',
        })
        self._create_invoice(partner=self.partner_international, sent=True, taxes=special_tax)
        with self.assertRaises(UserError) as ctx:
            self._aggregate_company()
        self.assertIn('VATEX-FR-CNWVAT', str(ctx.exception))

    def test_vatex_fr_cnwvat_allowed_on_credit_note(self):
        """VATEX-FR-CNWVAT should be allowed when the invoice is a credit note."""
        special_tax = self.tax_20.copy({
            'name': 'CNWVAT Tax Credit Note',
            'amount': 0.0,
            'l10n_fr_pdp_vatex_code': 'VATEX-FR-CNWVAT',
        })
        invoice = self._create_invoice(partner=self.partner_international, sent=True)
        refund = invoice._reverse_moves(default_values_list=[{
            'journal_id': invoice.journal_id.id,
            'invoice_date': invoice.invoice_date,
        }], cancel=False)
        for line in refund.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            line.tax_ids = [Command.set(special_tax.ids)]
        refund.action_post()
        refund.is_move_sent = True

        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(flow.payload, 'Credit note with VATEX-FR-CNWVAT should not block payload generation')
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        reason_code = payload_xml.findtext(".//Invoice[TypeCode='381']/TaxSubTotal/TaxCategory/TaxExemptionReasonCode")
        self.assertEqual(reason_code, 'VATEX-FR-CNWVAT')

    def test_pai_note_is_included_in_invoice_notes(self):
        """PAI note should be exported as a supported 10.1 IncludedNote subject."""
        invoice = self._create_invoice(partner=self.partner_international, sent=True)
        invoice.write({'l10n_fr_pdp_note_pai': 'Tiers payeur: ACME PAY'})
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        pai_note = payload_xml.find(".//Invoice/IncludedNote[Subject='PAI']/Content")
        self.assertIsNotNone(pai_note, 'PAI note should be present in invoice notes')
        self.assertEqual(pai_note.text, 'Tiers payeur: ACME PAY')

    def test_invalid_tt57_tax_rate_blocks_payload(self):
        """Unsupported VAT rate should raise validation error TT-57."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        fake_subtotals = [{
            'taxable_amount': 100.0,
            'tax_amount': 10.0,
            'tax_percent': 15.0,
            'tax_category_code': 'S',
            'tax_reason_code': False,
            'tax_reason': False,
        }]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._tax_subtotals', return_value=fake_subtotals):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('TT-57', str(ctx.exception))

    def test_inconsistent_totals_block_payload(self):
        """Invoice totals must match tax subtotals within tolerance (G1.53)."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        fake_subtotals = [{
            'taxable_amount': 10.0,
            'tax_amount': 1.0,
            'tax_percent': 20.0,
            'tax_category_code': 'S',
            'tax_reason_code': False,
            'tax_reason': False,
        }]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._tax_subtotals', return_value=fake_subtotals):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('G1.53', str(ctx.exception))

    def test_invalid_quantity_format_blocks_payload(self):
        """Line quantity must respect G1.15 numeric format constraints."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        fake_lines = [{
            'description': 'Bad qty',
            'quantity': 1.12345,
            'unit_code': 'C62',
            'price_unit': 10.0,
            'line_extension': 10.0,
            'price_unit_net': 10.0,
            'price_unit_gross': 10.0,
            'note': {'code': 'PRD', 'comment': 'Bad qty'},
        }]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._line_entries', return_value=fake_lines):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('G1.15', str(ctx.exception))

    def test_invalid_unit_price_format_blocks_payload(self):
        """Line unit prices must respect G1.16 numeric format constraints."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        fake_lines = [{
            'description': 'Bad price',
            'quantity': 1.0,
            'unit_code': 'C62',
            'price_unit': 10.1234567,
            'line_extension': 10.0,
            'price_unit_net': 10.1234567,
            'price_unit_gross': 10.1234567,
            'note': {'code': 'PRD', 'comment': 'Bad price'},
        }]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._line_entries', return_value=fake_lines):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('G1.16', str(ctx.exception))

    def test_inconsistent_line_net_gross_blocks_payload(self):
        """Line net price cannot exceed gross price (G1.55)."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        fake_lines = [{
            'description': 'Bad net gross',
            'quantity': 1.0,
            'unit_code': 'C62',
            'price_unit': 110.0,
            'line_extension': 110.0,
            'price_unit_net': 110.0,
            'price_unit_gross': 100.0,
            'note': {'code': 'PRD', 'comment': 'Bad net gross'},
        }]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._line_entries', return_value=fake_lines):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('G1.55', str(ctx.exception))

    def test_edi_filename_format_qual(self):
        """Payload filename must follow the QUAL EDI naming rules."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        filename = flow.payload_filename or flow._build_filename()
        prefix = 'FFE1025A_PPF262_PPF262'
        self.assertTrue(filename.startswith(prefix))
        self.assertTrue(filename.endswith('.xml'))
        suffix = filename[len(prefix):-4]
        self.assertEqual(len(suffix), 19)
        self.assertTrue(suffix.isalnum())
        self.assertEqual(suffix, suffix.upper())

    def test_international_invalid_vat_sets_error_moves(self):
        """Buyer VAT invalid on international invoice should be tracked in error_move_ids."""
        bad_partner = self.partner_international.with_context(no_vat_validation=True)
        bad_partner.vat = 'BE000'
        inv = self._create_invoice(partner=bad_partner, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(flow)

        self.assertIn(inv, flow.error_move_ids)
        self.assertEqual(flow.state, 'error')

    def test_discount_adds_allowance_and_tax_fallback(self):
        """Discounted lines create allowance charges and 0%% tax breakdown when no tax lines."""
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_international.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'name': 'Discounted line',
                'quantity': 1,
                'price_unit': 100,
                'discount': 10,
                'tax_ids': [Command.set([])],
                'account_id': self.income_account.id,
            })],
        })
        move.action_post()
        move.is_move_sent = True

        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))

        allowances = payload_xml.findall('.//Invoice/AllowanceCharge')
        self.assertTrue(allowances, 'AllowanceCharge node should be present when a discount exists')
        tax_subtotals = payload_xml.findall('.//Invoice/TaxSubTotal')
        percents = {node.find('TaxCategory/Percent').text for node in tax_subtotals}
        self.assertIn('0.0', percents)

    def test_payload_metadata_checksum_and_business_process(self):
        """Payload must include namespace/schema, checksum, business process, and PRD notes."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))

        self.assertEqual(payload_xml.tag, 'Report')
        tax_nodes = payload_xml.findall('.//TaxSubTotal')
        self.assertTrue(tax_nodes, 'TaxSubTotal casing should match the schema')

        bp = payload_xml.find('.//Invoice/BusinessProcess')
        self.assertIsNotNone(bp, 'BusinessProcess block should be present for invoices')
        self.assertEqual(bp.find('ID').text, 'B1')
        self.assertIn('urn.cpro.gouv.fr:1p0:ereporting', bp.find('TypeID').text)

        prd_code = payload_xml.find('.//Invoice/Line/Note/Code')
        self.assertEqual(prd_code.text, 'PRD')

    def test_missing_b2c_summary_triggers_validation_error(self):
        """When B2C transactions exist but summaries are empty, validation should fail."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_summaries', return_value=[]):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('must include aggregated B2C data', str(ctx.exception))

    def test_missing_vat_breakdown_in_summary_is_error(self):
        """B2C summary without VAT breakdown should raise validation error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        fake_summary = [{
            'date': flow._format_date(fields.Date.today()),
            'currency': flow.currency_id.name,
            'tax_due_date_type_code': '3',
            'category_code': flow._get_transaction_category_code('b2c'),
            'tax_exclusive_amount': 100,
            'tax_total': 0,
            'transactions_count': 1,
            'vat_breakdown': [],
        }]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_summaries', return_value=fake_summary):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('VAT breakdown', str(ctx.exception))

    def test_unsupported_note_subject_raises_error(self):
        """Notes with unsupported subjects should trigger validation error."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]

        def fake_notes(move):
            return [{'subject': 'BAD', 'content': 'Invalid'}]

        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._invoice_notes', lambda self, move: fake_notes(move)):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('unsupported note subject', str(ctx.exception))

    def test_issue_datetime_format_invalid(self):
        """Invalid issue datetime should raise validation error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._is_valid_issue_datetime', return_value=False):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('format 204', str(ctx.exception))

    def test_issue_datetime_year_out_of_range_invalid(self):
        """Issue datetime year must remain within 2000-2099 (G1.36)."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        flow.write({'issue_datetime': '1999-01-01 00:00:00'})
        with self.assertRaises(UserError) as ctx:
            flow._build_payload()
        self.assertIn('G1.36', str(ctx.exception))

    def test_period_date_year_out_of_range_invalid(self):
        """Period dates TT-17/TT-18 must remain within 2000-2099 (G1.36)."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        with patch(
            'odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._period_vals',
            return_value={'start_date': '19991231', 'end_date': '20250101'},
        ):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        message = str(ctx.exception)
        self.assertIn('TT-17', message)
        self.assertIn('G1.36', message)

    def test_payload_render_failure_raises_user_error(self):
        """XML render failure should raise UserError with details."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        with (
            patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._validate', return_value=None),
            patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.etree.fromstring', side_effect=etree.XMLSyntaxError('bad', None, 0, 0)),
        ):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('Failed to render transaction report', str(ctx.exception))

    def test_credit_note_includes_preceding_reference(self):
        """International credit note should include preceding invoice reference when linked."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        refund = inv._reverse_moves(default_values_list=[{
            'journal_id': inv.journal_id.id,
            'invoice_date': inv.invoice_date,
        }], cancel=False)
        refund.action_post()
        refund.is_move_sent = True
        refund.reversed_entry_id = inv
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(flow.payload, 'Flow should have payload')
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        ref = payload_xml.find('.//Invoice[TypeCode=\'381\']/ReferencedDocument')
        self.assertIsNotNone(ref, 'ReferencedDocument should be present on linked credit note')
        self.assertEqual(ref.findtext('ID'), inv.name)

    def test_credit_note_without_origin_has_no_preceding_reference(self):
        """Refund without reversed_entry should not include a preceding reference block."""
        refund = self._create_invoice(partner=self.partner_international, sent=True)
        refund.write({'move_type': 'out_refund'})
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(flow.payload, 'Flow should have payload')
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        ref = payload_xml.find('.//Invoice[TypeCode=\'381\']/ReferencedDocument')
        self.assertIsNone(ref, 'Refund without origin should not include ReferencedDocument')

    def test_bt3_262_maps_reference_and_type(self):
        """BT-3=262 should map TT-21=381 and use BT-12/BT-73 as reference."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        inv.write({
            'l10n_fr_pdp_bt3_code': '262',
            'l10n_fr_pdp_contract_reference': 'CONTRACT-REF',
            'l10n_fr_pdp_billing_period_start': fields.Date.from_string('2025-01-15'),
        })
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        invoice = payload_xml.find('.//Invoice[TypeCode=\'381\']')
        self.assertIsNotNone(invoice, 'Invoice should be present with type code 381')
        ref = invoice.find('ReferencedDocument')
        self.assertIsNotNone(ref, 'ReferencedDocument should be present when BT-3=262')
        self.assertEqual(ref.findtext('ID'), 'CONTRACT-REF')
        self.assertEqual(ref.findtext('IssueDate'), '20250115')

    def test_advance_invoice_unpaid_uses_b1_frame(self):
        """Advance invoice should use B1 frame while unpaid."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        inv.write({'l10n_fr_pdp_bt3_code': '386', 'l10n_fr_pdp_invoice_reference': 'INV-ADV-UNPAID'})
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        frame_code = payload_xml.findtext('.//Invoice[ID=\'INV-ADV-UNPAID\']/BusinessProcess/ID')
        self.assertEqual(frame_code, 'B1')

    def test_advance_invoice_paid_uses_b2_frame(self):
        """Advance invoice should use B2 frame once paid."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        inv.write({'l10n_fr_pdp_bt3_code': '386', 'l10n_fr_pdp_invoice_reference': 'INV-ADV-PAID'})
        self._create_payment_for_invoice(inv)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        frame_code = payload_xml.findtext('.//Invoice[ID=\'INV-ADV-PAID\']/BusinessProcess/ID')
        self.assertEqual(frame_code, 'B2')

    def test_final_invoice_with_advance_deduction_uses_b4_frame(self):
        """Final invoice with downpayment deduction should use B4 frame."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        inv.write({'l10n_fr_pdp_invoice_reference': 'INV-FINAL-B4'})
        with patch(
            'odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._is_final_invoice_with_advance_deduction',
            return_value=True,
        ):
            flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        frame_code = payload_xml.findtext('.//Invoice[ID=\'INV-FINAL-B4\']/BusinessProcess/ID')
        self.assertEqual(frame_code, 'B4')

    def test_multiple_preceding_references_are_exported(self):
        """Invoice should export all available document-level preceding references."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        inv.write({'l10n_fr_pdp_invoice_reference': 'INV-MULTI-REF'})
        refs = [
            {'id': 'ADV-001', 'issue_date': '20250110'},
            {'id': 'ADV-002', 'issue_date': '20250111'},
        ]
        with patch(
            'odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._preceding_invoice_refs',
            return_value=refs,
        ):
            flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        ref_nodes = payload_xml.findall('.//Invoice[ID=\'INV-MULTI-REF\']/ReferencedDocument')
        self.assertEqual(len(ref_nodes), 2)

    def test_line_preceding_reference_is_exported(self):
        """Line-level TT-300/TT-301 reference should be exported when available."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        inv.write({'l10n_fr_pdp_invoice_reference': 'INV-LINE-REF'})
        line_ref = {'id': 'INV-ORIGIN-001', 'issue_date': '20250120'}
        with patch(
            'odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._line_preceding_invoice_ref',
            return_value=line_ref,
        ):
            flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        ref_node = payload_xml.find('.//Invoice[ID=\'INV-LINE-REF\']/Line/ReferencedDocument')
        self.assertIsNotNone(ref_node)
        self.assertEqual(ref_node.findtext('ID'), 'INV-ORIGIN-001')
        self.assertEqual(ref_node.findtext('IssueDate'), '20250120')

    def test_bt8_transcoding_maps_tt24(self):
        """BT-8 values 29/35 must be transcoded to TT-24 values 5/3."""
        inv_29 = self._create_invoice(partner=self.partner_international, sent=True)
        inv_29.write({'l10n_fr_pdp_bt8_code': '29', 'l10n_fr_pdp_invoice_reference': 'INV-BT8-29'})
        inv_35 = self._create_invoice(partner=self.partner_international, sent=True)
        inv_35.write({'l10n_fr_pdp_bt8_code': '35', 'l10n_fr_pdp_invoice_reference': 'INV-BT8-35'})
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        code_29 = payload_xml.findtext('.//Invoice[ID=\'INV-BT8-29\']/TaxDueDateTypeCode')
        code_35 = payload_xml.findtext('.//Invoice[ID=\'INV-BT8-35\']/TaxDueDateTypeCode')
        self.assertEqual(code_29, '5')
        self.assertEqual(code_35, '3')

    def test_b2c_service_summary_uses_debits_due_code(self):
        """B2C TPS1 summary should expose due code 1 when service taxes are on debits."""
        service_tax_on_invoice = self.tax_20.copy({
            'name': 'VAT 20 Service Debits',
            'tax_scope': 'service',
            'tax_exigibility': 'on_invoice',
            'l10n_fr_pdp_tt81_category': 'TPS1',
        })
        inv = self._create_invoice(partner=self.partner_b2c, sent=True, product=self.service_product, taxes=service_tax_on_invoice)
        inv.write({'l10n_fr_pdp_invoice_reference': 'INV-TPS1-DEBITS'})
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        due_code = payload_xml.findtext('.//Transactions[CategoryCode=\'TPS1\']/TaxDueDateTypeCode')
        self.assertEqual(due_code, '1')

    def test_vatex_reason_mapping_and_nr(self):
        """VATEX mapping must populate missing text or code according to rules."""
        tax_code_only = self.tax_20.copy({
            'name': 'VATEX Code Only',
            'amount': 0.0,
            'l10n_fr_pdp_vatex_code': 'VATEX-EU-IC',
            'l10n_fr_pdp_vatex_reason': False,
        })
        inv_code_only = self._create_invoice(partner=self.partner_international, sent=True, taxes=tax_code_only)
        inv_code_only.write({'l10n_fr_pdp_invoice_reference': 'INV-VATEX-CODE'})

        tax_reason_only = self.tax_20.copy({
            'name': 'VATEX Reason Only',
            'amount': 0.0,
            'l10n_fr_pdp_vatex_code': False,
            'l10n_fr_pdp_vatex_reason': 'Custom VAT exemption reason',
        })
        inv_reason_only = self._create_invoice(partner=self.partner_international, sent=True, taxes=tax_reason_only)
        inv_reason_only.write({'l10n_fr_pdp_invoice_reference': 'INV-VATEX-REASON'})

        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))

        code_reason = payload_xml.find('.//Invoice[ID=\'INV-VATEX-CODE\']/TaxSubTotal/TaxCategory')
        self.assertEqual(code_reason.findtext('TaxExemptionReasonCode'), 'VATEX-EU-IC')
        self.assertEqual(code_reason.findtext('TaxExemptionReason'), 'Intra-Community supply')

        reason_only = payload_xml.find('.//Invoice[ID=\'INV-VATEX-REASON\']/TaxSubTotal/TaxCategory')
        self.assertEqual(reason_only.findtext('TaxExemptionReasonCode'), 'NR')
        self.assertEqual(reason_only.findtext('TaxExemptionReason'), 'Custom VAT exemption reason')

    def test_invoice_reference_override_used_in_payload(self):
        """Invoice reference override should replace the payload invoice ID."""
        inv = self._create_invoice(partner=self.partner_international, sent=True)
        inv.write({'l10n_fr_pdp_invoice_reference': 'REF-TEST-001'})
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        invoice_id = payload_xml.findtext('.//Invoice/ID')
        self.assertEqual(invoice_id, 'REF-TEST-001')

    def test_line_gross_and_net_prices(self):
        """TT-69/TT-71 should expose net and gross unit prices."""
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_international.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'name': 'Discounted line',
                'quantity': 1,
                'price_unit': 100,
                'discount': 10,
                'tax_ids': [Command.set(self.tax_20.ids)],
                'account_id': self.income_account.id,
            })],
        })
        move.action_post()
        move.is_move_sent = True
        move.write({'l10n_fr_pdp_invoice_reference': 'INV-PRICE'})
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        price_amount = payload_xml.findtext('.//Invoice[ID=\'INV-PRICE\']/Line/Price/PriceAmount')
        gross_amount = payload_xml.findtext('.//Invoice[ID=\'INV-PRICE\']/Line/Price/AllowanceChargeBaseAmount')
        self.assertAlmostEqual(float(price_amount), 90.0, places=2)
        self.assertAlmostEqual(float(gross_amount), 100.0, places=2)

    def test_send_uses_proxy_minimal_payload(self):
        """Flow send should call the proxy with minimal flow 10 payload."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        flow._build_payload()
        self.assertTrue(flow.payload)
        self.assertTrue(flow.payload_filename)
        response = flow._send_to_proxy()
        self.assertIn('id', response)
        self.assertIn('status', response)

    def test_allowance_with_tax_keeps_tax_percent(self):
        """Discount with tax should generate allowance including tax percent."""
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_international.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'name': 'Discounted',
                'quantity': 1,
                'price_unit': 100,
                'discount': 10,
                'tax_ids': [Command.set(self.tax_20.ids)],
                'account_id': self.income_account.id,
            })],
        })
        move.action_post()
        move.is_move_sent = True

        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        payload_xml = etree.fromstring(base64.b64decode(flow.payload))
        allowances = payload_xml.findall('.//Invoice/AllowanceCharge')
        self.assertTrue(allowances, 'AllowanceCharge should exist for discounted line with tax')
        percents = {node.findtext('TaxPercent') for node in allowances}
        self.assertTrue(any(p.startswith('20') for p in percents), 'TaxPercent should reflect the tax rate')

    def test_b2c_currency_mismatch_skips_precision_validation(self):
        """B2C summary in foreign currency should not trigger precision error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        fake_summary = [{
            'date': flow._format_date(fields.Date.today()),
            'currency': 'USD',
            'tax_due_date_type_code': '3',
            'category_code': flow._get_transaction_category_code('b2c'),
            'tax_exclusive_amount': 0.001,
            'tax_total': 0.0,
            'transactions_count': 1,
            'vat_breakdown': [{'vat_rate': 0.0, 'amount_untaxed': 0.001, 'amount_tax': 0.0}],
        }]
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._transaction_summaries', return_value=fake_summary):
            flow._build_payload()
        self.assertTrue(flow.payload, 'Payload should build even with foreign currency B2C summary')

    def test_xsd_validation_mode_off_skips_schema_loading(self):
        """XSD schema should not be loaded when validation mode is off."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        with (
            patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._get_xsd_validation_mode', return_value='off'),
            patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._get_ereporting_schema') as schema_loader,
        ):
            flow._build_payload()
        schema_loader.assert_not_called()

    def test_xsd_validation_mode_defaults_to_auto(self):
        """Unset validation mode should default to auto."""
        builder = PdpPayloadBuilder(self.env['l10n.fr.pdp.flow'])
        config = self.env['ir.config_parameter'].sudo()
        config.search([('key', '=', 'l10n_fr_pdp_reports.xsd_validation')]).unlink()
        self.assertEqual(builder._get_xsd_validation_mode(), 'auto')

    def test_xsd_validation_error_raises_user_error(self):
        """Invalid XML against XSD should raise a blocking UserError."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]

        class _SchemaError:
            line = 14
            message = "Element 'ReportDocument': Missing child element(s)."

        class _FakeSchema:
            error_log = [_SchemaError()]

            @staticmethod
            def assertValid(_xml_root):
                raise etree.DocumentInvalid("invalid xml")

        with (
            patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._get_xsd_validation_mode', return_value='auto'),
            patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._resolve_xsd_directory', return_value='/tmp/fake_xsd'),
            patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_payload.PdpPayloadBuilder._get_ereporting_schema', return_value=_FakeSchema()),
        ):
            with self.assertRaises(UserError) as ctx:
                flow._build_payload()
        self.assertIn('not compliant with AIFE XSD', str(ctx.exception))
