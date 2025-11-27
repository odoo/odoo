import base64
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from datetime import datetime
from functools import lru_cache

from lxml import etree

from odoo import fields, _
from odoo.exceptions import UserError
from odoo.tools import file_path, float_round, html2plaintext
from odoo.addons.account_edi_ubl_cii_tax_extension.models.account_edi_common import TAX_EXEMPTION_MAPPING
from odoo.addons.l10n_fr_pdp_reports.utils import drom_com_territories


class PdpPayloadBuilder:
    """Build and validate Flux 10 payloads for a flow"""

    def __init__(self, flow):
        self.flow = flow
        self.env = flow.env

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def build(self, moves, slice_date=None, invalid_collector=None):
        """Build XML payload for the given moves."""
        report_vals = (
            self._build_payment_report_vals(moves, invalid_collector)
            if self.flow.report_kind == 'payment'
            else self._build_transaction_report_vals(moves, invalid_collector)
        )
        self._validate(report_vals)
        rendered = self.env['ir.qweb']._render(
            'l10n_fr_pdp_reports.flux10_transaction_report',
            {'flow': self.flow, 'report': report_vals},
        )
        try:
            xml_root = etree.fromstring(rendered.encode('utf-8'))
            self._validate_xml_schema(xml_root)
            xml_content = etree.tostring(
                xml_root,
                xml_declaration=True,
                encoding='UTF-8',
            )
        except etree.XMLSyntaxError as err:
            raise UserError(_("Failed to render transaction report: %(error)s", error=err))
        return {
            'payload': base64.b64encode(xml_content),
            'filename': self._filename(slice_date),
        }

    def _validate_xml_schema(self, xml_root):
        """Validate generated XML against Flux 10 XSDs when enabled."""
        mode = self._get_xsd_validation_mode()
        if mode == 'off':
            return

        xsd_dir = self._resolve_xsd_directory()
        if not xsd_dir:
            if mode == 'strict':
                raise UserError(_(
                    "Flux 10 XSD validation is enabled in strict mode but XSD files were not found. "
                    "Set system parameter %(param)s to a valid XSD folder.",
                    param='l10n_fr_pdp_reports.xsd_dir',
                ))
            return

        try:
            schema = self._get_ereporting_schema(xsd_dir)
            schema.assertValid(xml_root)
        except etree.DocumentInvalid as err:
            details = self._format_schema_errors(schema.error_log)
            raise UserError(_("Generated Flux 10 XML is not compliant with AIFE XSD: %(details)s", details=details)) from err
        except (OSError, etree.XMLSchemaParseError, etree.XMLSyntaxError) as err:
            raise UserError(_("Unable to load Flux 10 XSD schema: %(error)s", error=err)) from err

    def _get_xsd_validation_mode(self):
        param_value = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('l10n_fr_pdp_reports.xsd_validation', 'auto')
            .strip()
            .lower()
        )
        return param_value if param_value in {'off', 'auto', 'strict'} else 'auto'

    def _resolve_xsd_directory(self):
        configured_dir = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('l10n_fr_pdp_reports.xsd_dir', '')
            .strip()
        )
        if configured_dir:
            if self._has_ereporting_schema(configured_dir):
                return configured_dir
            return None

        xsd_directory = 'l10n_fr_pdp_reports/data/xsd'
        if self._has_ereporting_schema(xsd_directory):
            return xsd_directory
        return None

    @staticmethod
    def _has_ereporting_schema(directory):
        if not directory:
            return False
        try:
            normalized_directory = directory.rstrip('/\\')
            xsd_relative_path = normalized_directory + '/ereporting.xsd'
            file_path(xsd_relative_path, filter_ext=('.xsd',))
            return True
        except (FileNotFoundError, ValueError):
            return False

    @staticmethod
    def _format_schema_errors(error_log):
        errors = [f"line {err.line}: {err.message}" for err in list(error_log)[:5]]
        return ' | '.join(errors) if errors else _("Unknown XSD validation error")

    @staticmethod
    @lru_cache(maxsize=8)
    def _get_ereporting_schema(xsd_directory):
        normalized_directory = xsd_directory.rstrip('/\\')
        xsd_relative_path = normalized_directory + '/ereporting.xsd'
        xsd_file = file_path(xsd_relative_path, filter_ext=('.xsd',))
        schema_doc = etree.parse(xsd_file)
        return etree.XMLSchema(schema_doc)

    # -------------------------------------------------------------------------
    # Report Builders
    # -------------------------------------------------------------------------

    def _build_transaction_report_vals(self, moves, invalid_collector=None):
        """Build values for TransactionReport (blocks 10.1 and 10.3)."""
        valid_moves, invalids = self.flow._filter_valid_moves(
            moves, invalid_collector=invalid_collector, log_event=True,
        )
        if invalid_collector is not None:
            invalid_collector.update(invalids)
        b2c_moves, international_moves = self._partition_moves(valid_moves)
        expected_types = {m._get_l10n_fr_pdp_transaction_type() for m in valid_moves}
        if self.flow.operation_type == 'purchase':
            expected_types = {'international'}
        return {
            'document': self._document_vals(),
            'period': self._period_vals(),
            'invoices': [self._invoice_vals(m) for m in international_moves],
            'transaction_summaries': self._transaction_summaries(b2c_moves, 'b2c'),
            'transaction_payments': [],
            'invoice_payments': [],
            'expected_b2c_transactions': 'b2c' in expected_types,
            'expected_international_invoices': 'international' in expected_types,
        }

    def _build_payment_report_vals(self, moves, invalid_collector=None):
        """Build values for PaymentReport (blocks 10.2 and 10.4)."""
        valid_moves, invalids = self.flow._filter_valid_moves(moves, invalid_collector=invalid_collector)
        if invalid_collector is not None:
            invalid_collector.update(invalids)
        b2c_moves, international_moves = self._partition_moves(valid_moves)
        invoice_payments = self._invoice_payments(international_moves)
        transaction_payments = self._transaction_payments(b2c_moves)
        return {
            'document': self._document_vals(),
            'period': self._period_vals(),
            'invoices': [],
            'transaction_summaries': [],
            'transaction_payments': transaction_payments,
            'invoice_payments': invoice_payments,
            'has_payment_content': bool(invoice_payments or transaction_payments),
        }

    # -------------------------------------------------------------------------
    # Data Extraction Helpers
    # -------------------------------------------------------------------------

    def _partition_moves(self, moves):
        """Split moves into B2C and international buckets."""
        if self.flow.operation_type == 'purchase':
            return self.env['account.move'].browse(), moves
        b2c = self.env['account.move'].browse()
        international = self.env['account.move'].browse()
        for move in moves:
            tx_type = move._get_l10n_fr_pdp_transaction_type()
            if tx_type == 'b2c':
                b2c |= move
            elif tx_type == 'international':
                international |= move
        return b2c, international

    def _b2c_line_category(self, line):
        """Return TT-81 category code for a B2C invoice line."""
        taxes = line.tax_ids
        for tax in taxes:
            category = (tax.l10n_fr_pdp_tt81_category or '').strip()
            if category:
                return category
        if any(
            (tax.l10n_fr_pdp_vatex_code or '').strip() or (tax.l10n_fr_pdp_vatex_reason or '').strip()
            for tax in taxes
        ):
            return 'TNT1'
        if taxes and all(float(tax.amount or 0.0) == 0.0 for tax in taxes):
            return 'TNT1'
        if any(tax.tax_scope == 'service' for tax in taxes):
            return 'TPS1'
        if any(tax.tax_scope == 'consu' for tax in taxes):
            return 'TLB1'
        if line.product_id and line.product_id.type == 'service':
            return 'TPS1'
        return 'TLB1'

    def _is_service_payment_line(self, line):
        """Return True when a line should contribute to payment reporting.

        Services with option débits (tax_exigibility='on_invoice') are excluded
        because TVA is already due at invoicing — no payment reporting needed.
        """
        taxes = line.tax_ids
        if line.product_id:
            is_service = line.product_id.type == 'service' or any(t.tax_scope == 'service' for t in taxes)
        else:
            is_service = any(
                (t.l10n_fr_pdp_tt81_category or '').strip() == 'TPS1' or t.tax_scope == 'service'
                for t in taxes
            )
        if not is_service:
            return False
        # Only report payments for services with TVA à l'encaissement (on_payment)
        return any(t.tax_exigibility == 'on_payment' for t in taxes) if taxes else True

    def _b2c_summary_buckets(self, moves):
        """Aggregate B2C amounts by day and TT-81 category."""
        currency = self.flow.currency_id or self.flow.company_id.currency_id
        grouped = defaultdict(lambda: {
            'move_ids': set(),
            'amount_untaxed': 0.0,
            'amount_tax': 0.0,
            'service_has_on_invoice': False,
            'service_has_on_payment': False,
            'vat_buckets': defaultdict(lambda: {'move_ids': set(), 'amount_untaxed': 0.0, 'amount_tax': 0.0}),
        })
        for move in moves:
            is_refund = move.move_type in ('out_refund', 'in_refund')
            move_date = move.invoice_date or move.date
            for line in move.invoice_line_ids.filtered(lambda ln: ln.display_type == 'product'):
                category = self._b2c_line_category(line)
                bucket = grouped[move_date, category]
                bucket['move_ids'].add(move.id)
                if category == 'TPS1':
                    line_taxes = line.tax_ids
                    bucket['service_has_on_invoice'] = (
                        bucket['service_has_on_invoice']
                        or any(tax.tax_exigibility == 'on_invoice' for tax in line_taxes)
                    )
                    bucket['service_has_on_payment'] = (
                        bucket['service_has_on_payment']
                        or any(tax.tax_exigibility == 'on_payment' for tax in line_taxes)
                    )
                line_untaxed = line.price_subtotal or 0.0
                line_tax = (line.price_total or 0.0) - (line.price_subtotal or 0.0)
                bucket['amount_untaxed'] += line_untaxed
                bucket['amount_tax'] += line_tax

                unit_price = (line.price_unit or 0.0) * (1 - (line.discount or 0.0) / 100.0)
                taxes_res = line.tax_ids.compute_all(
                    unit_price,
                    currency,
                    line.quantity,
                    product=line.product_id,
                    partner=move.partner_id,
                    is_refund=is_refund,
                )
                tax_items = taxes_res.get('taxes') or []
                if not tax_items:
                    vat_bucket = bucket['vat_buckets'][0.0]
                    vat_bucket['amount_untaxed'] += line_untaxed
                    vat_bucket['amount_tax'] += 0.0
                    vat_bucket['move_ids'].add(move.id)
                    continue
                for tax_item in tax_items:
                    base_amount = tax_item.get('base') or 0.0
                    tax_amount = tax_item.get('amount') or 0.0
                    vat_rate = float_round((tax_amount / base_amount) * 100.0, precision_digits=2) if base_amount else 0.0
                    vat_bucket = bucket['vat_buckets'][vat_rate]
                    vat_bucket['amount_untaxed'] += base_amount
                    vat_bucket['amount_tax'] += tax_amount
                    vat_bucket['move_ids'].add(move.id)
        return grouped

    def _document_vals(self):
        """Build document header values."""
        flow = self.flow
        company = flow.company_id
        flow._ensure_tracking_id()
        issue_dt = flow.issue_datetime or fields.Datetime.now()
        if isinstance(issue_dt, str):
            issue_dt = fields.Datetime.from_string(issue_dt)
        company_siret = company.siret or ''
        company_siren = company_siret[:9]
        declarant_siren = company.l10n_fr_pdp_declarant_siren or company_siren or str(company.id)
        sender_id = (company.l10n_fr_pdp_sender_id or '').strip() or '0129'
        issuer_role = 'BY' if flow.operation_type == 'purchase' else 'SE'
        # v1.2: No References block (transmission_reference/reference_scheme removed)
        return {
            'id': flow.tracking_id or flow.name,
            'name': _("Flux 10 Report %(date)s", date=flow.reporting_date),
            'issue_datetime': issue_dt.strftime('%Y%m%d%H%M%S'),
            'type_code': flow.transmission_type or 'IN',  # TT-4: only IN or RE
            'sender': {
                'scheme_id': '0238',  # 0238 = PA/PPF SIREN scheme (AFNOR table)
                'id': sender_id,
                'name': company.name,
                'role_code': 'WK',  # WK = platform/operator role
                'email': company.email or '',
            },
            'issuer': {
                'scheme_id': '0002',  # 0002 = French SIREN scheme for issuer
                'id': declarant_siren,
                'name': company.name,
                'role_code': issuer_role,  # SE = seller role, BY = buyer role
                'email': company.email or '',
            },
        }

    def _period_vals(self):
        """Build period values."""
        flow = self.flow
        return {
            'start_date': flow._format_date(flow.period_start or flow.reporting_date),
            'end_date': flow._format_date(flow.period_end or flow.reporting_date),
        }

    def _invoice_vals(self, move):
        """Build invoice values for international B2B (block 10.1)."""
        flow = self.flow
        company = move.company_id or flow.company_id
        is_purchase = move.is_purchase_document(include_receipts=False)
        seller_partner = move.commercial_partner_id if is_purchase else move.company_id.partner_id
        buyer_partner = move.company_id.partner_id if is_purchase else move.commercial_partner_id
        seller_is_company = not is_purchase
        buyer_is_company = is_purchase
        currency = move.currency_id or move.company_id.currency_id
        tax_due_code = self._tax_due_date_type_code(move, company)
        due_date = move.invoice_date_due or move.invoice_date or move.date
        invoice_id = self._invoice_identifier(move)
        type_code = self._invoice_type_code(move)
        preceding_refs = self._preceding_invoice_refs(move)
        return {
            'id': invoice_id,
            'issue_date': flow._format_date(move.invoice_date or move.date),
            'type_code': type_code,
            'currency': currency.name if currency else '',
            'due_date': flow._format_date(due_date),
            'tax_due_date_type_code': tax_due_code,
            'seller': self._party_vals(seller_partner, company=seller_is_company),
            'seller_fiscal_representative_vat': (
                company.l10n_fr_pdp_fiscal_representative_vat if not is_purchase else ''
            ),
            'buyer': self._party_vals(buyer_partner, company=buyer_is_company),
            'business_process': {'id': self._get_cadre_code(move), 'type_id': 'urn.cpro.gouv.fr:1p0:ereporting'},
            'invoice_period': {
                'start_date': flow._format_date(flow.period_start or move.invoice_date or move.date),
                'end_date': flow._format_date(flow.period_end or move.invoice_date_due or move.invoice_date or move.date),
            },
            'monetary_total': {
                'tax_exclusive_amount': abs(move.amount_untaxed),
                'tax_amount': self._to_eur(abs(move.amount_tax), currency, company, move.invoice_date or move.date),
                'tax_currency': 'EUR',
            },
            'tax_subtotals': self._tax_subtotals(move),
            'lines': self._line_entries(move),
            'notes': self._invoice_notes(move),
            'delivery': self._delivery_vals(move),
            'allowance_charges': self._allowance_charges(move),
            'preceding_invoice_references': preceding_refs,
            # Backward-compatible single reference.
            'preceding_invoice_reference': preceding_refs[0] if preceding_refs else False,
        }

    def _transaction_summaries(self, moves, transaction_type):
        """Build B2C transaction summary (block 10.3) per day and category.

        TVA amounts (TT-83/TT-88) are converted to EUR per G6.23.
        """
        if not moves:
            return []
        flow = self.flow
        company = flow.company_id
        flow_currency = flow.currency_id or company.currency_id
        tax_due_code = company.l10n_fr_pdp_tax_due_code or '3'
        summaries = []
        grouped = self._b2c_summary_buckets(moves)
        for (date, category_code), metrics in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
            summary_due_code = tax_due_code
            if category_code == 'TPS1':
                has_on_invoice = metrics.get('service_has_on_invoice')
                has_on_payment = metrics.get('service_has_on_payment')
                if has_on_invoice and not has_on_payment:
                    summary_due_code = '1'  # TVA sur les debits
                elif has_on_payment and not has_on_invoice:
                    summary_due_code = '3'  # TVA sur les encaissements
            vat_breakdown = sorted([{
                'vat_rate': rate,
                'transaction_count': len(vals['move_ids']),
                'amount_untaxed': vals['amount_untaxed'],
                'amount_tax': self._to_eur(vals['amount_tax'], flow_currency, company, date),
            } for rate, vals in metrics['vat_buckets'].items()], key=lambda e: e['vat_rate'])
            summaries.append({
                'date': flow._format_date(date),
                'currency': flow_currency.name if flow_currency else '',
                'tax_due_date_type_code': summary_due_code,
                'category_code': category_code,
                'tax_exclusive_amount': metrics['amount_untaxed'],
                'tax_total': self._to_eur(metrics['amount_tax'], flow_currency, company, date),
                'tax_currency': 'EUR',
                # TT-85 is optional for TMA1 (margin scheme).
                'transactions_count': None if category_code == 'TMA1' else len(metrics['move_ids']),
                'vat_breakdown': vat_breakdown,
            })
        return summaries

    def _transaction_payments(self, moves):
        """Build B2C transaction payments (block 10.4).

        Payment amounts (TT-99) are converted to EUR per G6.27.
        """
        payments_by_date = defaultdict(lambda: defaultdict(float))
        flow = self.flow
        company = flow.company_id
        flow_currency = flow.currency_id or company.currency_id
        for move in moves:
            total_invoice = move.amount_total or 0.0
            if not total_invoice:
                continue
            is_refund = move.move_type in ('out_refund', 'in_refund')
            is_advance = self._is_advance_payment_move(move)
            service_buckets = defaultdict(float)
            for line in move.invoice_line_ids.filtered(lambda ln: ln.display_type == 'product'):
                if not (is_advance or self._is_service_payment_line(line)):
                    continue
                unit_price = (line.price_unit or 0.0) * (1 - (line.discount or 0.0) / 100.0)
                taxes_res = line.tax_ids.compute_all(
                    unit_price,
                    flow_currency,
                    line.quantity,
                    product=line.product_id,
                    partner=move.partner_id,
                    is_refund=is_refund,
                )
                tax_items = taxes_res.get('taxes') or []
                line_total = line.price_total or 0.0
                if not tax_items:
                    service_buckets[0.0] += line_total
                    continue
                for tax_item in tax_items:
                    base_amount = tax_item.get('base') or 0.0
                    tax_amount = tax_item.get('amount') or 0.0
                    vat_rate = float_round((tax_amount / base_amount) * 100.0, precision_digits=2) if base_amount else 0.0
                    service_buckets[vat_rate] += base_amount + tax_amount
            if not service_buckets:
                continue

            def _add_payment_amount(amount, payment_date):
                if not amount:
                    return
                for vat_rate, bucket_amount in service_buckets.items():
                    allocated = amount * (bucket_amount / total_invoice)
                    if allocated:
                        payments_by_date[payment_date][vat_rate] += allocated

            if move.move_type == 'out_receipt':
                payment_date = flow._format_date(move.invoice_date or move.date)
                _add_payment_amount(move.amount_total or 0.0, payment_date)
            else:
                for partial in move._get_all_reconciled_invoice_partials():
                    aml = partial.get('aml')
                    if not aml:
                        continue
                    if not self._is_payment_partial_aml(aml):
                        continue
                    amount = self._payment_amount(partial, aml, flow_currency, move.currency_id)
                    if amount:
                        _add_payment_amount(amount, flow._format_date(aml.date))
            for event in self._pending_unreconcile_events(move):
                _add_payment_amount(event.amount, flow._format_date(event.event_date))
        payments = []
        convert_date = flow.period_end or flow.reporting_date
        for date, vat_buckets in sorted(payments_by_date.items()):
            subtotals = sorted([{
                'tax_percent': rate,
                'currency': 'EUR',
                'amount': self._to_eur(amount, flow_currency, company, convert_date),
            } for rate, amount in vat_buckets.items() if amount], key=lambda item: item['tax_percent'])
            if not subtotals:
                continue
            payments.append({
                'date': date,
                'currency': 'EUR',
                'subtotals': subtotals,
            })
        return payments

    def _invoice_payments(self, moves):
        """Build international invoice payments (block 10.2).

        Payment amounts (TT-95) are converted to EUR per G6.27.
        """
        payments = []
        flow = self.flow
        company = flow.company_id
        flow_currency = flow.currency_id or company.currency_id
        for move in moves:
            total_invoice = move.amount_total or 0.0
            if not total_invoice:
                continue
            is_refund = move.move_type in ('out_refund', 'in_refund')
            is_advance = self._is_advance_payment_move(move)
            service_buckets = defaultdict(float)
            for line in move.invoice_line_ids.filtered(lambda ln: ln.display_type == 'product'):
                if not (is_advance or self._is_service_payment_line(line)):
                    continue
                unit_price = (line.price_unit or 0.0) * (1 - (line.discount or 0.0) / 100.0)
                taxes_res = line.tax_ids.compute_all(
                    unit_price,
                    flow_currency,
                    line.quantity,
                    product=line.product_id,
                    partner=move.partner_id,
                    is_refund=is_refund,
                )
                tax_items = taxes_res.get('taxes') or []
                line_total = line.price_total or 0.0
                if not tax_items:
                    service_buckets[0.0] += line_total
                    continue
                for tax_item in tax_items:
                    base_amount = tax_item.get('base') or 0.0
                    tax_amount = tax_item.get('amount') or 0.0
                    vat_rate = float_round((tax_amount / base_amount) * 100.0, precision_digits=2) if base_amount else 0.0
                    service_buckets[vat_rate] += base_amount + tax_amount
            if not service_buckets:
                continue
            for partial in move._get_all_reconciled_invoice_partials():
                aml = partial.get('aml')
                if not aml:
                    continue
                if not self._is_payment_partial_aml(aml):
                    continue
                amount = self._payment_amount(partial, aml, flow_currency, move.currency_id)
                if not amount:
                    continue
                payment_currency = partial.get('currency') or move.currency_id or flow_currency
                subtotals = []
                for vat_rate, bucket_amount in sorted(service_buckets.items()):
                    allocated = amount * (bucket_amount / total_invoice)
                    if allocated:
                        subtotals.append({
                            'tax_percent': vat_rate,
                            'currency': 'EUR',
                            'amount': self._to_eur(allocated, payment_currency, company, aml.date),
                        })
                if not subtotals:
                    continue
                payments.append({
                    'invoice_id': self._invoice_identifier(move),
                    'issue_date': flow._format_date(move.invoice_date or move.date),
                    'payment': {
                        'date': flow._format_date(aml.date),
                        'subtotals': subtotals,
                    },
                })
            for event in self._pending_unreconcile_events(move):
                subtotals = []
                for vat_rate, bucket_amount in sorted(service_buckets.items()):
                    allocated = event.amount * (bucket_amount / total_invoice)
                    if allocated:
                        subtotals.append({
                            'tax_percent': vat_rate,
                            'currency': 'EUR',
                            'amount': self._to_eur(allocated, flow_currency, company, event.event_date),
                        })
                if not subtotals:
                    continue
                payments.append({
                    'invoice_id': self._invoice_identifier(move),
                    'issue_date': flow._format_date(move.invoice_date or move.date),
                    'payment': {
                        'date': flow._format_date(event.event_date),
                        'subtotals': subtotals,
                    },
                })
        return sorted(payments, key=lambda v: (v['payment']['date'], v['invoice_id']))

    # -------------------------------------------------------------------------
    # Invoice Component Helpers
    # -------------------------------------------------------------------------

    def _line_entries(self, move):
        """Build invoice line entries."""
        return [
            self._line_entry_vals(line)
            for line in move.invoice_line_ids
        ]

    def _line_entry_vals(self, line):
        """Build a single invoice line entry."""
        quantity = line.quantity or 0.0
        gross_unit_price = abs(line.price_unit or 0.0)
        net_unit_price = abs(line.price_subtotal / quantity) if quantity else 0.0
        return {
            'description': line.name or '',
            'quantity': quantity,
            'unit_code': line.product_uom_id.l10n_fr_pdp_unit_code if line.product_uom_id and 'l10n_fr_pdp_unit_code' in line.product_uom_id._fields else None,
            'price_unit': line.price_unit or 0.0,
            'line_extension': abs(line.price_subtotal),
            'price_unit_net': net_unit_price,
            'price_unit_gross': gross_unit_price,
            'note': {'code': 'PRD', 'comment': line.name} if line.name else False,
            'preceding_invoice_reference': self._line_preceding_invoice_ref(line),
        }

    def _invoice_notes(self, move):
        """Build invoice notes (AAB/BLU/TXD/PAI per Flux 10.1 requirements)."""
        notes = []
        if move.narration:
            notes.append({
                'subject': 'AAB',
                'content': html2plaintext(move.narration).strip(),
            })
        if move.l10n_fr_pdp_note_blu:
            notes.append({'subject': 'BLU', 'content': move.l10n_fr_pdp_note_blu})
        if move.l10n_fr_pdp_note_txd:
            notes.append({'subject': 'TXD', 'content': move.l10n_fr_pdp_note_txd})
        if 'l10n_fr_pdp_note_pai' in move._fields and move.l10n_fr_pdp_note_pai:
            notes.append({'subject': 'PAI', 'content': move.l10n_fr_pdp_note_pai})
        return notes

    def _delivery_vals(self, move):
        """Build delivery address values."""
        partner = move.partner_shipping_id
        if not partner:
            return {}

        delivery_country_code = partner.country_id.code if partner.country_id else ''

        # Country codes for DROM-COM territories are mapped to 'FR' for PPF transmission.
        mapped_country_code = drom_com_territories.map_country_code_for_ppf(delivery_country_code)

        return {
            'date': self.flow._format_date(move.invoice_date or move.date),
            'name': partner.name or '',
            'line1': partner.street or '',
            'line2': partner.street2 or '',
            'city': partner.city or '',
            'postal_zone': partner.zip or '',
            'country': mapped_country_code,
        }

    def _allowance_charges(self, move):
        """Build allowance/charge entries from line discounts."""
        allowances = []
        for line in move.invoice_line_ids:
            if not line.discount:
                continue
            base_amount = line.price_unit * line.quantity
            amount = abs(base_amount * (line.discount / 100.0))
            if not amount:
                continue
            if line.tax_ids:
                for tax in line.tax_ids:
                    allowances.append({
                        'is_charge': False,
                        'amount': amount,
                        'tax_category_code': tax.l10n_fr_code if 'l10n_fr_code' in tax._fields else 'S',  # S = standard VAT
                        'tax_percent': tax.amount or 0.0,
                        'charge_indicator': False,
                    })
            else:
                allowances.append({
                    'is_charge': False,
                    'amount': amount,
                    'tax_category_code': 'E',  # E = exempt/zero VAT
                    'tax_percent': 0.0,
                    'charge_indicator': False,
                })
        return allowances

    def _tax_subtotals(self, move):
        """Build tax breakdown entries with TVA amounts converted to EUR (G6.23)."""
        subtotals = []
        company = move.company_id or self.flow.company_id
        currency = move.currency_id or company.currency_id
        date = move.invoice_date or move.date
        for tax_line in move.line_ids.filtered(lambda ln: ln.tax_line_id):
            tax = tax_line.tax_line_id
            tax_reason_code, tax_reason = self._vat_exemption_reason(tax)
            subtotals.append({
                'taxable_amount': abs(tax_line.tax_base_amount),
                'tax_amount': self._to_eur(abs(tax_line.balance), currency, company, date),
                'tax_percent': tax.amount or 0.0,
                'tax_category_code': self._get_tax_category_code(tax),
                'tax_reason': tax_reason,
                'tax_reason_code': tax_reason_code,
            })
        if not subtotals:
            taxes = move.invoice_line_ids.mapped('tax_ids')
            if taxes:
                tax_buckets = {}
                for line in move.invoice_line_ids:
                    base_amount = abs(line.price_subtotal)
                    for tax in line.tax_ids:
                        bucket = tax_buckets.setdefault(tax.id, {'tax': tax, 'base': 0.0, 'amount': 0.0})
                        bucket['base'] += base_amount
                        bucket['amount'] += abs(base_amount * (tax.amount or 0.0) / 100.0)
                for bucket in tax_buckets.values():
                    tax = bucket['tax']
                    tax_reason_code, tax_reason = self._vat_exemption_reason(tax)
                    subtotals.append({
                        'taxable_amount': bucket['base'],
                        'tax_amount': self._to_eur(bucket['amount'], currency, company, date),
                        'tax_percent': tax.amount or 0.0,
                        'tax_category_code': self._get_tax_category_code(tax),
                        'tax_reason': tax_reason,
                        'tax_reason_code': tax_reason_code,
                    })
            else:
                subtotals.append({
                    'taxable_amount': abs(move.amount_untaxed),
                    'tax_amount': self._to_eur(abs(move.amount_tax), currency, company, date),
                    'tax_percent': 0.0,
                    'tax_category_code': 'E',
                    'tax_reason': False,
                    'tax_reason_code': False,
                })
        return subtotals

    def _preceding_invoice_refs(self, move):
        """Build all document-level TT-30/TT-31 references."""
        refs = []
        if (move.l10n_fr_pdp_bt3_code or '').strip() == '262':
            ref_id = (move.l10n_fr_pdp_contract_reference or '').strip()
            ref_date = move.l10n_fr_pdp_billing_period_start
            if ref_id and ref_date:
                refs.append({
                    'id': ref_id,
                    'issue_date': self.flow._format_date(ref_date),
                })

        is_refund = move.move_type in ('out_refund', 'in_refund')
        if is_refund:
            origin = move.reversed_entry_id or (move.debit_origin_id if 'debit_origin_id' in move._fields else False)
            if origin:
                refs.append({
                    'id': origin.name,
                    'issue_date': self.flow._format_date(origin.invoice_date or origin.date),
                })

        refs.extend(self._advance_invoice_refs(move))
        unique_refs = {}
        for ref in refs:
            ref_id = (ref.get('id') or '').strip()
            issue_date = ref.get('issue_date')
            if not ref_id:
                continue
            unique_refs[ref_id, issue_date] = {'id': ref_id, 'issue_date': issue_date}
        return sorted(unique_refs.values(), key=lambda r: (r.get('issue_date') or '', r['id']))

    def _preceding_invoice_ref(self, move):
        """Backward-compatible single TT-30/TT-31 reference."""
        refs = self._preceding_invoice_refs(move)
        return refs[0] if refs else False

    def _advance_invoice_refs(self, move):
        """Return references to linked advance invoices used in a final invoice."""
        refs = {}
        for line in move.invoice_line_ids.filtered(lambda ln: ln.display_type == 'product'):
            if 'is_downpayment' not in line._fields or not line.is_downpayment:
                continue
            if 'sale_line_ids' not in line._fields:
                continue
            for sale_line in line.sale_line_ids:
                if 'invoice_lines' not in sale_line._fields:
                    continue
                for invoice_line in sale_line.invoice_lines:
                    previous_move = invoice_line.move_id
                    if not previous_move or previous_move == move or previous_move.state != 'posted':
                        continue
                    if not self._is_advance_payment_move(previous_move):
                        continue
                    ref_id = self._invoice_identifier(previous_move)
                    if not ref_id:
                        continue
                    refs[previous_move.id] = {
                        'id': ref_id,
                        'issue_date': self.flow._format_date(previous_move.invoice_date or previous_move.date),
                    }
        return list(refs.values())

    def _line_preceding_invoice_ref(self, line):
        """Build optional line-level TT-300/TT-301 reference."""
        if 'sale_line_ids' not in line._fields:
            return False
        refs = []
        current_move = line.move_id
        for sale_line in line.sale_line_ids:
            if 'invoice_lines' not in sale_line._fields:
                continue
            for invoice_line in sale_line.invoice_lines:
                previous_move = invoice_line.move_id
                if not previous_move or previous_move == current_move or previous_move.state != 'posted':
                    continue
                ref_id = self._invoice_identifier(previous_move)
                if not ref_id:
                    continue
                refs.append((ref_id, previous_move.invoice_date or previous_move.date))
        if not refs:
            return False
        ref_id, ref_date = sorted(refs, key=lambda vals: (vals[1] or fields.Date.today(), vals[0]))[0]
        return {
            'id': ref_id,
            'issue_date': self.flow._format_date(ref_date) if ref_date else False,
        }

    def _party_vals(self, partner, company=False):
        """Build party (seller/buyer) values."""
        partner = partner.commercial_partner_id
        partner_siret = partner.siret or ''
        partner_country_code = partner.country_id.code if partner.country_id else ''

        # Country codes for DROM-COM territories are mapped to 'FR' for PPF transmission
        mapped_country_code = drom_com_territories.map_country_code_for_ppf(partner_country_code)

        # Check for specific identifier schemes (RIDET, TAHITI, etc.)
        specific_scheme = drom_com_territories.get_specific_identifier_scheme(partner_country_code)

        # Determine company scheme and ID
        if specific_scheme and partner.ref:
            # Use specific identifier for territories like NC (RIDET), PF (TAHITI), WF
            company_scheme = specific_scheme['qualifier']
            company_id = partner.ref
        elif company and partner_siret:
            # Standard French SIREN
            company_scheme = '0002'
            company_id = partner_siret[:9]
        elif partner.vat:
            # VAT scheme
            company_scheme = '0223'
            company_id = partner.vat
        else:
            company_scheme = False
            company_id = partner.ref or ''

        return {
            'company_scheme': company_scheme,
            'company_id': company_id,
            'vat': partner.vat or '',
            'street': partner.street or '',
            'street2': partner.street2 or '',
            'city': partner.city or '',
            'postal_zone': partner.zip or '',
            'country': mapped_country_code,
        }

    def _invoice_identifier(self, move):
        """Return the invoice identifier used in Flux 10 payloads."""
        return (move.l10n_fr_pdp_invoice_reference or move.name or '').strip()

    def _to_eur(self, amount, currency, company, date):
        """Convert amount to EUR for TVA reporting (G6.23/G6.27)."""
        eur = self.env.ref('base.EUR')
        if currency == eur:
            return amount
        return currency._convert(amount, eur, company, date)

    def _get_tax_category_code(self, tax):
        """Determine CII tax category code from tax configuration."""
        if vatex_code := (tax.l10n_fr_pdp_vatex_code or '').strip():
            if vatex_code.startswith('VATEX-EU-AE'):
                return 'AE'
            if vatex_code.startswith('VATEX-EU-D'):
                return 'K'
            if vatex_code.startswith('VATEX-EU-G'):
                return 'G'
            if vatex_code.startswith('VATEX-EU-O'):
                return 'O'
            return 'E'
        if tax.amount:
            return 'S'
        return 'Z'

    def _get_cadre_code(self, move):
        """Determine billing framework code (TT-28) from invoice content/lifecycle."""
        base_prefix = self._get_cadre_prefix(move)
        if self._is_advance_payment_move(move):
            return f'{base_prefix}2' if self._is_invoice_fully_paid(move) else f'{base_prefix}1'
        if self._is_final_invoice_with_advance_deduction(move):
            return f'{base_prefix}4'
        return f'{base_prefix}1'

    def _get_cadre_prefix(self, move):
        """Return TT-28 base prefix by scope: B (goods), S (services), M (mixed)."""
        scopes = set()
        for line in move.invoice_line_ids.filtered(lambda ln: ln.display_type == 'product'):
            for tax in line.tax_ids:
                if tax.tax_scope:
                    scopes.add(tax.tax_scope)
        has_goods = 'consu' in scopes
        has_services = 'service' in scopes
        if has_goods and has_services:
            return 'M'
        if has_services:
            return 'S'
        return 'B'

    def _invoice_type_code(self, move):
        """Return TT-21 invoice type code based on BT-3 or move type."""
        bt3_code = (move.l10n_fr_pdp_bt3_code or '').strip()
        if bt3_code:
            return '381' if bt3_code == '262' else bt3_code
        is_refund = move.move_type in ('out_refund', 'in_refund')
        return '381' if is_refund else '380'

    def _tax_due_date_type_code(self, move, company):
        """Return TT-24 based on BT-8 with required transcodings."""
        bt8_code = (move.l10n_fr_pdp_bt8_code or '').strip()
        if bt8_code == '29':
            return '5'
        if bt8_code == '35':
            return '3'
        return bt8_code or (company.l10n_fr_pdp_tax_due_code or '3')

    def _vat_exemption_reason(self, tax):
        """Return VATEX reason code and text with BR-FR-MAP-25..28 rules."""
        code = (tax.l10n_fr_pdp_vatex_code or '').strip()
        reason = (tax.l10n_fr_pdp_vatex_reason or '').strip()
        if not code and 'l10n_fr_code' in tax._fields:
            code = (tax.l10n_fr_code or '').strip()
        if not reason and 'l10n_fr_note' in tax._fields:
            reason = (tax.l10n_fr_note or '').strip()

        if code and not reason:
            reason = TAX_EXEMPTION_MAPPING.get(code)
        if reason and not code:
            code = 'NR'
        return code or False, reason or False

    def _payment_amount(self, partial, aml, flow_currency, move_currency):
        """Extract payment amount from partial reconciliation."""
        amount = partial.get('amount')
        if amount is None:
            if aml.currency_id and aml.currency_id == (flow_currency or move_currency):
                amount = aml.amount_currency
            else:
                amount = aml.balance
        return amount or 0.0

    def _is_payment_partial_aml(self, aml):
        """Return True when a reconciled AML corresponds to an actual payment."""
        move = aml.move_id
        has_origin_payment = 'origin_payment_id' in move._fields and bool(move.origin_payment_id)
        has_statement_line = 'statement_line_id' in move._fields and bool(move.statement_line_id)
        return has_origin_payment or has_statement_line

    def _is_advance_payment_move(self, move):
        """Return True when payment reporting must include all lines (advance invoices)."""
        bt3_code = (move.l10n_fr_pdp_bt3_code or '').strip()
        if bt3_code in {'386', '500'}:
            return True
        lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        return any('is_downpayment' in line._fields and line.is_downpayment for line in lines)

    def _is_invoice_fully_paid(self, move):
        """Return True if invoice residual is fully cleared."""
        currency = move.currency_id or move.company_currency_id
        residual = move.amount_residual or 0.0
        if currency:
            return currency.is_zero(residual)
        return abs(residual) <= 0.01

    def _is_final_invoice_with_advance_deduction(self, move):
        """Return True for final invoice containing downpayment deductions."""
        lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        downpayment_lines = lines.filtered(lambda l: 'is_downpayment' in l._fields and l.is_downpayment)
        if not downpayment_lines:
            return False
        has_regular_lines = any(not ('is_downpayment' in line._fields and line.is_downpayment) for line in lines)
        has_deduction_line = any((line.price_subtotal or 0.0) < 0 for line in downpayment_lines)
        return has_regular_lines and has_deduction_line

    def _pending_unreconcile_events(self, move):
        """Return pending unreconcile events for move within this flow period."""
        flow = self.flow
        domain = [
            ('move_id', '=', move.id),
            ('state', '=', 'pending'),
        ]
        if flow.period_start:
            domain.append(('event_date', '>=', flow.period_start))
        if flow.period_end:
            domain.append(('event_date', '<=', flow.period_end))
        return self.env['l10n.fr.pdp.payment.event'].sudo().search(domain, order='event_date,id')

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def _validate(self, report_vals):
        """Validate report values before XML generation."""
        flow = self.flow
        document = report_vals.get('document') or {}
        currency = flow.currency_id or flow.company_id.currency_id
        company_partner = flow.company_id.partner_id
        errors = []

        # Company validation
        if not self._digits(flow.company_id.siret or company_partner.siret):
            errors.append(_("Company %(company)s is missing its SIRET/SIREN.", company=flow.company_id.display_name))
        if not currency:
            errors.append(_("Flow %(name)s has no currency defined.", name=flow.name))
        if not company_partner.vat and not self._can_use_fiscal_representative_without_company_vat(report_vals):
            errors.append(_("Company %(company)s is missing its VAT number.", company=flow.company_id.display_name))

        # Document validation
        doc_id = document.get('id') or flow.name or ''
        if not self._is_valid_transmission_identifier(doc_id):
            errors.append(_("Transmission identifier '%(identifier)s' does not respect TT-1 formatting rules.", identifier=doc_id))
        issue_dt = document.get('issue_datetime') or ''
        if not issue_dt:
            errors.append(_("Flow %(name)s is missing the issue datetime (TT-3).", name=flow.name))
        elif not self._is_valid_issue_datetime(issue_dt):
            errors.append(_("Issue datetime '%(value)s' must follow format 204 (AAAAMMJJHHMMSS) with year between 2000 and 2099 (G1.36).", value=issue_dt))
        period = report_vals.get('period') or {}
        for key, label in (
            ('start_date', 'TT-17'),
            ('end_date', 'TT-18'),
        ):
            period_date = (period.get(key) or '').strip()
            if not period_date:
                errors.append(_("Reporting period %(label)s is missing.", label=label))
            elif not self._is_valid_report_date(period_date):
                errors.append(
                    _("Reporting period %(label)s '%(value)s' must follow format 102 (AAAAMMJJ) with year between 2000 and 2099 (G1.36).",
                      label=label, value=period_date)
                )
        sender_id = ((document.get('sender') or {}).get('id') or '').strip()
        if not sender_id:
            errors.append(_("Sender matricule (TT-8) is missing."))
        elif len(sender_id) != 4:
            errors.append(_("Sender matricule (TT-8) must be 4 characters."))
        issuer_id = ((document.get('issuer') or {}).get('id') or '').strip()
        if issuer_id and len(self._digits(issuer_id)) != 9:
            errors.append(_("Issuer SIREN (TT-13) must be 9 digits."))

        # Content validation
        self._validate_invoices(report_vals, currency, errors)
        self._validate_summaries(report_vals, currency, errors)
        self._validate_payments(report_vals, currency, errors)

        if errors:
            raise UserError('\n'.join(errors))

    def _validate_invoices(self, report_vals, currency, errors):
        """Validate invoice entries."""
        flow = self.flow
        invoices = report_vals.get('invoices') or []
        allowed_type_codes = self._valid_invoice_type_codes()
        seen_invoice_identities = set()
        if (flow.report_kind == 'transaction' and
                report_vals.get('expected_international_invoices') and
                not invoices and not flow.error_move_ids):
            errors.append(_("Flow %(name)s must contain at least one international invoice.", name=flow.name))

        for invoice in invoices:
            invoice_id = invoice.get('id') or _("Invoice without identifier")
            if not self._is_valid_invoice_identifier(invoice.get('id') or ''):
                errors.append(
                    _("Invoice %(invoice)s has an invalid identifier (TT-19). "
                      "Expected max 20 characters using alphanumerics, space, -, +, _, /.",
                      invoice=invoice_id)
                )
            type_code = (invoice.get('type_code') or '').strip()
            if type_code and type_code not in allowed_type_codes:
                errors.append(
                    _("Invoice %(invoice)s has an unsupported type code '%(code)s' (TT-21).",
                      invoice=invoice_id, code=type_code)
                )
            frame_code = ((invoice.get('business_process') or {}).get('id') or '').strip()
            if frame_code in {'B4', 'S4', 'M4'} and type_code in {'386', '500'}:
                errors.append(
                    _("Invoice %(invoice)s has an incompatible frame/type combination (G1.60): "
                      "%(frame)s cannot be used with TT-21=%(type)s.",
                      invoice=invoice_id, frame=frame_code, type=type_code)
                )
            issue_date = (invoice.get('issue_date') or '').strip()
            if not issue_date:
                errors.append(_("Invoice %(invoice)s is missing its issue date (TT-20).", invoice=invoice_id))
            elif not self._is_valid_report_date(issue_date):
                errors.append(
                    _("Invoice %(invoice)s has invalid issue date '%(value)s' (G1.36).",
                      invoice=invoice_id, value=issue_date)
                )
            due_date = (invoice.get('due_date') or '').strip()
            if due_date and not self._is_valid_report_date(due_date):
                errors.append(
                    _("Invoice %(invoice)s has invalid due date '%(value)s' (G1.36).",
                      invoice=invoice_id, value=due_date)
                )
            seller_values = invoice.get('seller') or {}
            seller_identifier = seller_values.get('company_id') or seller_values.get('id')
            seller_siren = self._digits(seller_identifier)[:9]
            duplicate_key = (invoice_id, issue_date[:4], seller_siren)
            if all(duplicate_key):
                if duplicate_key in seen_invoice_identities:
                    errors.append(
                        _("Invoice %(invoice)s is duplicated in transmission (G1.42): "
                          "same TT-19, TT-20 year and seller SIREN.",
                          invoice=invoice_id)
                    )
                else:
                    seen_invoice_identities.add(duplicate_key)
            due_code = (invoice.get('tax_due_date_type_code') or '').strip()
            if not due_code:
                errors.append(_("Invoice %(invoice)s is missing the tax due date type code (TT-64).", invoice=invoice_id))
            elif not flow._is_valid_due_date_code(due_code):
                errors.append(_("Invoice %(invoice)s has an invalid tax due date type code '%(code)s'.", invoice=invoice_id, code=due_code))
            invoice_period = invoice.get('invoice_period') or {}
            for period_key, period_label in (
                ('start_date', 'TT-42'),
                ('end_date', 'TT-43'),
            ):
                invoice_period_date = (invoice_period.get(period_key) or '').strip()
                if invoice_period_date and not self._is_valid_report_date(invoice_period_date):
                    errors.append(
                        _("Invoice %(invoice)s has invalid %(label)s '%(value)s' (G1.36).",
                          invoice=invoice_id, label=period_label, value=invoice_period_date)
                    )
            preceding_refs = invoice.get('preceding_invoice_references') or []
            if not preceding_refs and invoice.get('preceding_invoice_reference'):
                preceding_refs = [invoice.get('preceding_invoice_reference')]
            for preceding_ref in preceding_refs:
                preceding_issue_date = (preceding_ref.get('issue_date') or '').strip()
                if preceding_issue_date and not self._is_valid_report_date(preceding_issue_date):
                    errors.append(
                        _("Invoice %(invoice)s has invalid preceding invoice issue date '%(value)s' (G1.36).",
                          invoice=invoice_id, value=preceding_issue_date)
                    )

            self._check_seller_vat_or_fiscal_representative(invoice_id, invoice, errors)
            self._check_vat(invoice_id, invoice.get('buyer') or {}, 'buyer', errors)

            for note in invoice.get('notes') or []:
                subject = note.get('subject')
                if subject and subject not in self._valid_note_subjects():
                    errors.append(_("Invoice %(invoice)s references unsupported note subject '%(subject)s'.", invoice=invoice_id, subject=subject))

            self._check_invoice_line_constraints(invoice_id, invoice.get('lines') or [], errors)
            self._check_invoice_totals_consistency(invoice_id, invoice, errors)

            if currency and invoice.get('currency') == currency.name:
                self._check_amounts(invoice_id, currency, invoice.get('monetary_total') or {}, ('tax_exclusive_amount', 'tax_amount'), errors)
                for subtotal in invoice.get('tax_subtotals') or []:
                    if subtotal.get('tax_percent') is None:
                        errors.append(_("Invoice %(invoice)s is missing a tax rate in its breakdown.", invoice=invoice_id))
                    elif not self._has_valid_percentage_format(subtotal.get('tax_percent')):
                        errors.append(
                            _("Invoice %(invoice)s has invalid tax rate format '%(rate)s' (G1.24).",
                              invoice=invoice_id, rate=subtotal.get('tax_percent'))
                        )
                    elif not self._is_valid_vat_rate(subtotal.get('tax_percent')):
                        errors.append(
                            _("Invoice %(invoice)s has unsupported VAT rate '%(rate)s' (TT-57).",
                              invoice=invoice_id, rate=subtotal.get('tax_percent'))
                        )
                    self._check_amounts(invoice_id, currency, subtotal, ('taxable_amount', 'tax_amount'), errors)
                    exemption_code = (
                        subtotal.get('tax_exemption_reason_code')
                        or subtotal.get('tax_reason_code')
                        or ''
                    ).strip()
                    if exemption_code == 'VATEX-FR-CNWVAT' and type_code not in {'261', '381', '396', '502', '503'}:
                        errors.append(
                            _("Invoice %(invoice)s uses VATEX-FR-CNWVAT, which is allowed only on credit notes.",
                              invoice=invoice_id)
                        )
                for allowance in invoice.get('allowance_charges') or []:
                    self._check_amounts(invoice_id, currency, allowance, ('amount',), errors)
                    if allowance.get('tax_percent') is None:
                        errors.append(_("Invoice %(invoice)s has an allowance/charge without a tax rate.", invoice=invoice_id))
                    elif not self._has_valid_percentage_format(allowance.get('tax_percent')):
                        errors.append(
                            _("Invoice %(invoice)s has invalid allowance/charge tax rate format '%(rate)s' (G1.24).",
                              invoice=invoice_id, rate=allowance.get('tax_percent'))
                        )

    def _validate_summaries(self, report_vals, currency, errors):
        """Validate B2C summary entries."""
        flow = self.flow
        summaries = report_vals.get('transaction_summaries') or []
        valid_categories = {'TLB1', 'TPS1', 'TNT1', 'TMA1'}
        if (flow.report_kind == 'transaction' and
                report_vals.get('expected_b2c_transactions') and
                not summaries and not flow.error_move_ids):
            errors.append(_("Flow %(name)s must include aggregated B2C data.", name=flow.name))

        for summary in summaries:
            summary_date = (summary.get('date') or '').strip()
            if not summary_date:
                errors.append(_("B2C summary is missing date (TT-77)."))
            elif not self._is_valid_report_date(summary_date):
                errors.append(
                    _("B2C summary has invalid date '%(value)s' (G1.36).", value=summary_date)
                )
            due_code = (summary.get('tax_due_date_type_code') or '').strip()
            if due_code and not flow._is_valid_due_date_code(due_code):
                errors.append(_("B2C summary for %(date)s has an invalid tax due date type code '%(code)s'.", date=summary.get('date'), code=due_code))
            category_code = (summary.get('category_code') or '').strip()
            if category_code not in valid_categories:
                errors.append(_("B2C summary for %(date)s has an invalid category code '%(code)s'.", date=summary.get('date'), code=category_code))
            vat_breakdown = summary.get('vat_breakdown') or []
            if not vat_breakdown:
                errors.append(_("B2C summary for %(date)s is missing the VAT breakdown (TT-78).", date=summary.get('date')))
            if currency and summary.get('currency') == currency.name:
                self._check_amounts(summary.get('date'), currency, summary, ('tax_exclusive_amount', 'tax_total'), errors, summary=True)
                for vat_bucket in vat_breakdown:
                    if vat_bucket.get('vat_rate') is None:
                        errors.append(_("B2C summary for %(date)s is missing a VAT rate in the breakdown.", date=summary.get('date')))
                    elif not self._has_valid_percentage_format(vat_bucket.get('vat_rate')):
                        errors.append(
                            _("B2C summary for %(date)s has invalid VAT rate format '%(rate)s' (G1.24).",
                              date=summary.get('date'), rate=vat_bucket.get('vat_rate'))
                        )
                    elif not self._is_valid_vat_rate(vat_bucket.get('vat_rate')):
                        errors.append(
                            _("B2C summary for %(date)s has unsupported VAT rate '%(rate)s' (TT-57).",
                              date=summary.get('date'), rate=vat_bucket.get('vat_rate'))
                        )
                    self._check_amounts(summary.get('date'), currency, vat_bucket, ('amount_untaxed', 'amount_tax'), errors, summary=True)

    def _validate_payments(self, report_vals, currency, errors):
        """Validate payment entries."""
        if self.flow.report_kind != 'payment' or not currency:
            return
        payments = report_vals.get('invoice_payments') or report_vals.get('transaction_payments') or []
        for payment in payments:
            payment_date = (payment.get('date') or '').strip()
            if payment_date and not self._is_valid_report_date(payment_date):
                errors.append(
                    _("Payment %(payment)s has invalid date '%(value)s' (G1.36).",
                      payment=payment.get('id') or payment.get('invoice_id') or payment.get('date'),
                      value=payment_date)
                )
            payment_block = payment.get('payment') or {}
            payment_block_date = (payment_block.get('date') or '').strip()
            if payment_block_date and not self._is_valid_report_date(payment_block_date):
                errors.append(
                    _("Payment %(payment)s has invalid nested date '%(value)s' (G1.36).",
                      payment=payment.get('id') or payment.get('invoice_id') or payment_block_date,
                      value=payment_block_date)
                )
            payment_issue_date = (payment.get('issue_date') or '').strip()
            if payment_issue_date and not self._is_valid_report_date(payment_issue_date):
                errors.append(
                    _("Payment %(payment)s has invalid invoice issue date '%(value)s' (G1.36).",
                      payment=payment.get('id') or payment.get('invoice_id') or payment_block_date,
                      value=payment_issue_date)
                )
            payment_currency = payment.get('currency')
            if payment_currency and payment_currency != currency.name:
                continue
            self._check_amounts(payment.get('id') or payment.get('date'), currency, payment, ('amount',), errors, payment=True)
            for subtotal in payment.get('subtotals') or []:
                if subtotal.get('tax_percent') is not None and not self._has_valid_percentage_format(subtotal.get('tax_percent')):
                    errors.append(
                        _("Payment %(payment)s has invalid VAT rate format '%(rate)s' (G1.24).",
                          payment=payment.get('id') or payment.get('date'), rate=subtotal.get('tax_percent'))
                    )
                elif subtotal.get('tax_percent') is not None and not self._is_valid_vat_rate(subtotal.get('tax_percent')):
                    errors.append(
                        _("Payment %(payment)s has unsupported VAT rate '%(rate)s' (TT-57).",
                          payment=payment.get('id') or payment.get('date'), rate=subtotal.get('tax_percent'))
                    )
                self._check_amounts(payment.get('id') or payment.get('date'), currency, subtotal, ('amount',), errors, payment=True)

    # -------------------------------------------------------------------------
    # Validation Helpers
    # -------------------------------------------------------------------------

    def _check_vat(self, ref, party_vals, label, errors):
        """Check VAT number presence and validity."""
        vat = party_vals.get('vat')
        if not vat:
            if label == 'seller':
                errors.append(_("Invoice %(invoice)s requires a seller VAT number (TT-31).", invoice=ref))
            else:
                errors.append(_("Invoice %(invoice)s requires a buyer VAT number (TT-54).", invoice=ref))
        elif not self.flow._is_valid_vat(vat, party_vals.get('country')):
            errors.append(_("Invoice %(invoice)s has an invalid %(label)s VAT '%(vat)s'.", invoice=ref, label=label, vat=vat))

    def _check_seller_vat_or_fiscal_representative(self, ref, invoice, errors):
        """Validate seller VAT, with TT-122 fallback on exempt invoices."""
        seller_vals = invoice.get('seller') or {}
        seller_vat = (seller_vals.get('vat') or '').strip()
        if seller_vat:
            if not self.flow._is_valid_vat(seller_vat, seller_vals.get('country')):
                errors.append(
                    _("Invoice %(invoice)s has an invalid seller VAT '%(vat)s'.",
                      invoice=ref, vat=seller_vat)
                )
            return

        tax_subtotals = invoice.get('tax_subtotals') or []
        has_exempt_category = any(
            (subtotal.get('tax_category_code') or '').strip() == 'E'
            for subtotal in tax_subtotals
        )
        representative_vat = (invoice.get('seller_fiscal_representative_vat') or '').strip()
        if has_exempt_category:
            if not representative_vat:
                errors.append(
                    _("Invoice %(invoice)s requires TT-122 (seller fiscal representative VAT) "
                      "when seller VAT is missing and tax category E is used.",
                      invoice=ref)
                )
                return
            if not self.flow._is_valid_vat(representative_vat, seller_vals.get('country')):
                errors.append(
                    _("Invoice %(invoice)s has an invalid TT-122 fiscal representative VAT '%(vat)s'.",
                      invoice=ref, vat=representative_vat)
                )
            return

        errors.append(_("Invoice %(invoice)s requires a seller VAT number (TT-31).", invoice=ref))

    def _can_use_fiscal_representative_without_company_vat(self, report_vals):
        """Allow missing company VAT only when all exported invoices use TT-122 fallback."""
        invoices = report_vals.get('invoices') or []
        if not invoices:
            return False
        for invoice in invoices:
            tax_subtotals = invoice.get('tax_subtotals') or []
            has_exempt_category = any(
                (subtotal.get('tax_category_code') or '').strip() == 'E'
                for subtotal in tax_subtotals
            )
            representative_vat = (invoice.get('seller_fiscal_representative_vat') or '').strip()
            if not (has_exempt_category and representative_vat):
                return False
        return True

    def _check_amounts(self, ref, currency, data, keys, errors, summary=False, payment=False):
        """Check amount precision against currency."""
        for key in keys:
            amount = data.get(key)
            if amount is None:
                continue
            if not self._has_valid_amount_precision(amount, currency):
                if payment:
                    errors.append(_("Payment %(payment)s exceeds currency precision.", payment=ref))
                elif summary:
                    errors.append(_("B2C summary for %(date)s has %(field)s outside the currency precision.", date=ref, field=key))
                else:
                    errors.append(_("Invoice %(invoice)s has %(field)s outside the currency precision.", invoice=ref, field=key))

    def _check_invoice_totals_consistency(self, invoice_id, invoice, errors):
        """Validate document totals consistency against tax subtotals (G1.53)."""
        monetary_total = invoice.get('monetary_total') or {}
        tax_subtotals = invoice.get('tax_subtotals') or []
        if not tax_subtotals:
            return

        tax_exclusive_amount = monetary_total.get('tax_exclusive_amount')
        if tax_exclusive_amount is not None:
            sum_taxable = sum((subtotal.get('taxable_amount') or 0.0) for subtotal in tax_subtotals)
            if not self._is_close_amount(tax_exclusive_amount, sum_taxable):
                errors.append(
                    _("Invoice %(invoice)s has inconsistent totals (G1.53): "
                      "TT-51 differs from sum of TT-54.",
                      invoice=invoice_id)
                )

        tax_amount = monetary_total.get('tax_amount')
        if tax_amount is not None:
            sum_tax = sum((subtotal.get('tax_amount') or 0.0) for subtotal in tax_subtotals)
            if not self._is_close_amount(tax_amount, sum_tax):
                errors.append(
                    _("Invoice %(invoice)s has inconsistent totals (G1.53): "
                      "TT-52 differs from sum of TT-55.",
                      invoice=invoice_id)
                )

    def _check_invoice_line_constraints(self, invoice_id, lines, errors):
        """Validate line numeric constraints and net/gross coherence (G1.15/G1.16/G1.55)."""
        for index, line in enumerate(lines, start=1):
            quantity = line.get('quantity')
            if quantity is not None and not self._has_valid_numeric_format(quantity, 19, 4, allow_negative=False):
                errors.append(
                    _("Invoice %(invoice)s line %(line)s has invalid quantity format (G1.15).",
                      invoice=invoice_id, line=index)
                )

            for field_name in ('price_unit', 'price_unit_net', 'price_unit_gross'):
                value = line.get(field_name)
                if value is None:
                    continue
                if not self._has_valid_numeric_format(value, 19, 6, allow_negative=False):
                    errors.append(
                        _("Invoice %(invoice)s line %(line)s has invalid %(field)s format (G1.16).",
                          invoice=invoice_id, line=index, field=field_name)
                    )

            gross_price = line.get('price_unit_gross')
            net_price = line.get('price_unit_net')
            if gross_price is not None and net_price is not None and (net_price - gross_price) > 0.01:
                errors.append(
                    _("Invoice %(invoice)s line %(line)s has inconsistent net/gross prices (G1.55).",
                      invoice=invoice_id, line=index)
                )

            preceding_ref = line.get('preceding_invoice_reference') or {}
            preceding_issue_date = (preceding_ref.get('issue_date') or '').strip()
            if preceding_issue_date and not self._is_valid_report_date(preceding_issue_date):
                errors.append(
                    _("Invoice %(invoice)s line %(line)s has invalid preceding invoice issue date '%(value)s' (G1.36).",
                      invoice=invoice_id, line=index, value=preceding_issue_date)
                )

    def _has_valid_amount_precision(self, amount, currency):
        """Check if amount respects currency decimal places."""
        if amount is None or not currency:
            return True
        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            return False
        rounded = currency.round(amount_value)
        tolerance = 10 ** -(currency.decimal_places + 3)  # allow a tiny epsilon beyond currency precision
        return abs(rounded - amount_value) <= tolerance

    def _has_valid_numeric_format(self, value, max_integer_digits, max_decimal_digits, allow_negative=True):
        """Check numeric format constraints."""
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return False
        if not allow_negative and decimal_value < 0:
            return False

        _, digits, exponent = decimal_value.as_tuple()
        if exponent >= 0:
            integer_digits = len(digits) + exponent
            decimal_digits = 0
        else:
            decimal_digits = -exponent
            integer_digits = max(len(digits) - decimal_digits, 0)

        return integer_digits <= max_integer_digits and decimal_digits <= max_decimal_digits

    def _is_close_amount(self, amount_a, amount_b, tolerance=0.01):
        """Return True when both amounts are equal within tolerance."""
        return abs(float(amount_a or 0.0) - float(amount_b or 0.0)) <= tolerance

    def _has_valid_percentage_format(self, value):
        """Validate percentage format (max 3 integer digits and 2 decimals)."""
        return self._has_valid_numeric_format(value, 3, 2, allow_negative=False)

    def _is_valid_transmission_identifier(self, identifier):
        """Validate TT-1 transmission identifier format."""
        if not identifier or identifier.strip() != identifier:
            return False
        if len(identifier) > 50 or '  ' in identifier:
            return False
        return bool(re.fullmatch(r'[A-Za-z0-9 _+\-/]+', identifier))

    def _is_valid_invoice_identifier(self, identifier):
        """Validate TT-19 invoice identifier format."""
        if not identifier or identifier.strip() != identifier:
            return False
        if len(identifier) > 20 or '  ' in identifier:
            return False
        return bool(re.fullmatch(r'[A-Za-z0-9 _+\-/]+', identifier))

    def _is_valid_issue_datetime(self, value):
        """Validate TT-3 issue datetime format (YYYYMMDDHHMMSS)."""
        if not value or len(value) != 14 or not value.isdigit():
            return False
        try:
            parsed = datetime.strptime(value, '%Y%m%d%H%M%S')
            return 2000 <= parsed.year <= 2099
        except ValueError:
            return False

    def _is_valid_report_date(self, value):
        """Validate TT date fields format (YYYYMMDD) and year range (G1.36)."""
        if not value or len(value) != 8 or not value.isdigit():
            return False
        try:
            parsed = datetime.strptime(value, '%Y%m%d')
            return 2000 <= parsed.year <= 2099
        except ValueError:
            return False

    def _valid_note_subjects(self):
        """Return set of valid note subject codes per spec."""
        return {'AAB', 'BLU', 'TXD', 'PAI'}

    def _valid_invoice_type_codes(self):
        """Return valid TT-21 invoice type codes (UNTDID 1001)."""
        return {
            '380', '381', '384', '386', '389', '393', '396',
            '500', '501', '502', '503', '918', '919', '920', '261',
        }

    def _valid_vat_rates(self):
        """Return valid TT-57 VAT rates for Flux 10."""
        return {
            0.0, 0.9, 1.05, 1.75, 2.1, 5.5, 7.0, 8.5, 9.2, 9.6,
            10.0, 13.0, 19.6, 20.0, 20.6,
        }

    def _is_valid_vat_rate(self, rate):
        """Return True when VAT rate belongs to the allowed TT-57 list."""
        try:
            rate_value = float(rate)
        except (TypeError, ValueError):
            return False
        return any(abs(rate_value - allowed) <= 1e-6 for allowed in self._valid_vat_rates())

    def _digits(self, value):
        """Extract only digits from value."""
        return ''.join(ch for ch in (value or '') if ch.isdigit())

    def _filename(self, slice_date):
        """Generate payload filename."""
        filename = self.flow._build_filename()
        if slice_date:
            filename = filename.replace('.xml', f'_{slice_date}.xml')
        return filename
