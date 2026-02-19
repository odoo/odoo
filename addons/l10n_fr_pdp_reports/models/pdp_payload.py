import base64
import hashlib
from collections import defaultdict
from datetime import datetime
from lxml import etree
from odoo import _, fields
from odoo.exceptions import UserError
from odoo.tools import float_compare, html2plaintext


class PdpPayloadBuilder:
    """Build and validate Flux 10 payloads for a flow.

    This is a plain Python class (not an Odoo model) as recommended by guidelines
    for utility classes that don't need ORM features.
    """

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
            xml_content = etree.tostring(
                etree.fromstring(rendered.encode('utf-8')),
                xml_declaration=True,
                encoding='UTF-8',
            )
        except etree.XMLSyntaxError as err:
            raise UserError(_("Failed to render transaction report: %(error)s", error=err))
        return {
            'payload': base64.b64encode(xml_content),
            'filename': self._filename(slice_date),
            'sha256': hashlib.sha256(xml_content).hexdigest(),  # nosec: spec requires SHA-256 checksum
        }

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
        b2c = self.env['account.move'].browse()
        international = self.env['account.move'].browse()
        for move in moves:
            tx_type = move._get_l10n_fr_pdp_transaction_type()
            if tx_type == 'b2c':
                b2c |= move
            elif tx_type == 'international':
                international |= move
        return b2c, international

    def _summary_metrics(self, moves):
        """Compute aggregated metrics for B2C moves."""
        currency = self.flow.currency_id or self.flow.company_id.currency_id
        precision = currency.decimal_places if currency else 2
        vat_buckets = defaultdict(lambda: {'move_ids': set(), 'amount_untaxed': 0.0, 'amount_tax': 0.0})
        for move in moves:
            total_untaxed = abs(move.amount_untaxed)
            allocated = 0.0
            for tax_line in move.line_ids.filtered(lambda ln: ln.tax_line_id):
                tax = tax_line.tax_line_id
                vat_rate = float(tax.amount or 0.0)
                bucket = vat_buckets[vat_rate]
                base_amount = abs(tax_line.tax_base_amount or 0.0)
                tax_amount = abs(tax_line.balance or 0.0)
                allocated += base_amount
                bucket['amount_untaxed'] += base_amount
                bucket['amount_tax'] += tax_amount
                bucket['move_ids'].add(move.id)
            remaining = total_untaxed - allocated
            if float_compare(remaining, 0.0, precision_digits=precision) > 0:
                vat_buckets[0.0]['amount_untaxed'] += remaining
                vat_buckets[0.0]['move_ids'].add(move.id)
        vat_breakdown = sorted([{
            'vat_rate': rate,
            'transaction_count': len(vals['move_ids']),
            'amount_untaxed': vals['amount_untaxed'],
            'amount_tax': vals['amount_tax'],
        } for rate, vals in vat_buckets.items()], key=lambda e: e['vat_rate'])
        return {
            'currency': currency.name if currency else '',
            'transaction_count': len(moves),
            'amount_untaxed': sum(abs(m.amount_untaxed) for m in moves),
            'amount_tax': sum(abs(m.amount_tax) for m in moves),
            'amount_total': sum(abs(m.amount_total) for m in moves),
            'vat_breakdown': vat_breakdown,
        }

    def _document_vals(self):
        """Build document header values."""
        flow = self.flow
        company = flow.company_id
        issue_dt = flow.issue_datetime or fields.Datetime.now()
        if isinstance(issue_dt, str):
            issue_dt = fields.Datetime.from_string(issue_dt)
        company_siret = company.siret or ''
        company_siren = company_siret[:9]
        references = False
        if flow.transmission_reference:
            references = {
                'id': flow.transmission_reference,
                'type': flow.transmission_reference_type or 'IN',
                'scheme_id': 'ID',
            }
        return {
            'id': flow.name,
            'name': _("Flux 10 Report %(date)s", date=flow.reporting_date),
            'issue_datetime': issue_dt.strftime('%Y%m%d%H%M%S'),
            'type_code': flow.transmission_type or 'CO',
            'sender': {
                'scheme_id': '0238',  # 0238 = PA/PPF SIREN scheme (AFNOR table)
                'id': company_siren or str(company.id),
                'name': company.name,
                'role_code': 'WK',  # WK = platform/operator role
                'email': company.email or '',
            },
            'issuer': {
                'scheme_id': '0002',  # 0002 = French SIREN scheme for issuer
                'id': company_siren or str(company.id),
                'name': company.name,
                'role_code': 'SE',  # SE = seller role
                'email': company.email or '',
            },
            'references': references,
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
        currency = move.currency_id or move.company_id.currency_id
        tax_due_code = company.l10n_fr_pdp_tax_due_code or '3'  # TT-64 default to Encaissements when unset
        return {
            'id': move.name,
            'issue_date': flow._format_date(move.invoice_date or move.date),
            'type_code': '381' if move.move_type == 'out_refund' else '380',
            'currency': currency.name if currency else '',
            'due_date': flow._format_date(move.invoice_date_due) if move.invoice_date_due else '',
            'tax_due_date_type_code': tax_due_code,
            'seller': self._party_vals(move.company_id.partner_id, company=True),
            'buyer': self._party_vals(move.commercial_partner_id),
            'business_process': {'id': 'S1', 'type_id': 'urn.cpro.gouv.fr:1p0:ereporting'},  # S1 = e-reporting process id
            'invoice_period': {
                'start_date': flow._format_date(flow.period_start or move.invoice_date or move.date),
                'end_date': flow._format_date(flow.period_end or move.invoice_date_due or move.invoice_date or move.date),
            },
            'monetary_total': {
                'tax_exclusive_amount': abs(move.amount_untaxed),
                'tax_amount': abs(move.amount_tax),
            },
            'tax_subtotals': self._tax_subtotals(move),
            'lines': self._line_entries(move),
            'notes': self._invoice_notes(move),
            'delivery': self._delivery_vals(move),
            'allowance_charges': self._allowance_charges(move),
            'preceding_invoice_reference': self._preceding_invoice_ref(move),
        }

    def _transaction_summaries(self, moves, transaction_type):
        """Build B2C transaction summary (block 10.3) per day."""
        if not moves:
            return []
        flow = self.flow
        company = flow.company_id
        tax_due_code = company.l10n_fr_pdp_tax_due_code or '3'

        grouped = defaultdict(self.env['account.move'].browse)
        for move in moves:
            move_date = move.invoice_date or move.date
            grouped[move_date] |= move

        summaries = []
        for date, date_moves in sorted(grouped.items()):
            metrics = self._summary_metrics(date_moves)
            summaries.append({
                'date': flow._format_date(date),
                'currency': metrics['currency'],
                'tax_due_date_type_code': tax_due_code,
                'category_code': flow._get_transaction_category_code(transaction_type),
                'tax_exclusive_amount': metrics['amount_untaxed'],
                'tax_total': metrics['amount_tax'],
                'transactions_count': metrics['transaction_count'],
                'vat_breakdown': metrics['vat_breakdown'],
            })
        return summaries

    def _transaction_payments(self, moves):
        """Build B2C transaction payments (block 10.4)."""
        payments_by_date = defaultdict(float)
        flow_currency = self.flow.currency_id or self.flow.company_id.currency_id
        for move in moves:
            if move.move_type == 'out_receipt':
                payment_date = self.flow._format_date(move.invoice_date or move.date)
                payments_by_date[payment_date] += abs(move.amount_total)
                continue
            for partial in move._get_all_reconciled_invoice_partials():
                if aml := partial.get('aml'):
                    amount = self._payment_amount(partial, aml, flow_currency, move.currency_id)
                    if amount:
                        payments_by_date[self.flow._format_date(aml.date)] += amount
        return [{
            'date': date,
            'currency': flow_currency.name if flow_currency else '',
            'subtotals': [{'tax_percent': 0.0, 'currency': flow_currency.name if flow_currency else '', 'amount': amount}],
        } for date, amount in sorted(payments_by_date.items()) if amount]

    def _invoice_payments(self, moves):
        """Build international invoice payments (block 10.2, XSD-compliant)."""
        payments = []
        flow = self.flow
        flow_currency = flow.currency_id or flow.company_id.currency_id
        for move in moves:
            for partial in move._get_all_reconciled_invoice_partials():
                aml = partial.get('aml')
                if not aml:
                    continue
                amount = self._payment_amount(partial, aml, flow_currency, move.currency_id)
                if not amount:
                    continue
                currency_record = partial.get('currency') or move.currency_id or flow_currency
                payments.append({
                    'invoice_id': move.name,
                    'issue_date': flow._format_date(move.invoice_date or move.date),
                    'payment': {
                        'date': flow._format_date(aml.date),
                        'subtotals': [{
                            'tax_percent': 0.0,
                            'currency': currency_record.name if currency_record else '',
                            'amount': amount,
                        }],
                    },
                })
        return sorted(payments, key=lambda v: (v['payment']['date'], v['invoice_id']))

    # -------------------------------------------------------------------------
    # Invoice Component Helpers
    # -------------------------------------------------------------------------

    def _line_entries(self, move):
        """Build invoice line entries."""
        return [{
            'description': line.name or '',
            'quantity': line.quantity or 0.0,
            'unit_code': line.product_uom_id.l10n_fr_pdp_unit_code if line.product_uom_id and 'l10n_fr_pdp_unit_code' in line.product_uom_id._fields else None,
            'price_unit': line.price_unit or 0.0,
            'line_extension': abs(line.price_subtotal),
            'note': {'code': 'PRD', 'comment': line.name} if line.name else False,
        } for line in move.invoice_line_ids]

    def _invoice_notes(self, move):
        """Build invoice notes (PMT for payment terms, AAB for narration)."""
        notes = []
        if move.invoice_payment_term_id and move.invoice_payment_term_id.note:
            notes.append({'subject': 'PMT', 'content': move.invoice_payment_term_id.note})
        if move.narration:
            notes.append({
                'subject': 'AAB',
                'content': html2plaintext(move.narration).strip(),
            })
        return notes

    def _delivery_vals(self, move):
        """Build delivery address values."""
        partner = move.partner_shipping_id
        if not partner:
            return {}
        return {
            'date': self.flow._format_date(move.invoice_date or move.date),
            'name': partner.name or '',
            'line1': partner.street or '',
            'line2': partner.street2 or '',
            'city': partner.city or '',
            'postal_zone': partner.zip or '',
            'country': partner.country_id.code if partner.country_id else '',
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
        """Build tax breakdown entries."""
        subtotals = []
        for tax_line in move.line_ids.filtered(lambda ln: ln.tax_line_id):
            tax = tax_line.tax_line_id
            subtotals.append({
                'taxable_amount': abs(tax_line.tax_base_amount),
                'tax_amount': abs(tax_line.balance),
                'tax_percent': tax.amount or 0.0,
                'tax_category_code': 'S' if tax.amount else 'E',  # S=standard, E=exempt/zero
                'tax_reason': tax.l10n_fr_note if 'l10n_fr_note' in tax._fields else False,
                'tax_reason_code': tax.l10n_fr_code if 'l10n_fr_code' in tax._fields else False,
            })
        if not subtotals:
            subtotals.append({
                'taxable_amount': abs(move.amount_untaxed),
                'tax_amount': abs(move.amount_tax),
                'tax_percent': 0.0,
                'tax_category_code': 'E',
                'tax_reason': False,
                'tax_reason_code': False,
            })
        return subtotals

    def _preceding_invoice_ref(self, move):
        """Build preceding invoice reference for credit notes."""
        if move.move_type != 'out_refund':
            return False
        origin = move.reversed_entry_id or (move.debit_origin_id if 'debit_origin_id' in move._fields else False)
        if not origin:
            return False
        return {
            'id': origin.name,
            'issue_date': self.flow._format_date(origin.invoice_date or origin.date),
        }

    def _party_vals(self, partner, company=False):
        """Build party (seller/buyer) values."""
        partner = partner.commercial_partner_id
        partner_siret = partner.siret or ''
        return {
            'company_scheme': '0002' if company and partner_siret else ('0223' if partner.vat else False),  # 0002=SIREN, 0223=VAT scheme
            'company_id': partner_siret[:9] if company and partner_siret else (partner.vat or partner.ref or ''),
            'vat': partner.vat or '',
            'street': partner.street or '',
            'street2': partner.street2 or '',
            'city': partner.city or '',
            'postal_zone': partner.zip or '',
            'country': partner.country_id.code if partner.country_id else '',
        }

    def _payment_amount(self, partial, aml, flow_currency, move_currency):
        """Extract payment amount from partial reconciliation."""
        amount = partial.get('amount')
        if amount is None:
            if aml.currency_id and aml.currency_id == (flow_currency or move_currency):
                amount = abs(aml.amount_currency)
            else:
                amount = abs(aml.balance)
        return amount or 0.0

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
        if not company_partner.vat:
            errors.append(_("Company %(company)s is missing its VAT number.", company=flow.company_id.display_name))

        # Document validation
        doc_id = document.get('id') or flow.name or ''
        if not self._is_valid_transmission_identifier(doc_id):
            errors.append(_("Transmission identifier '%(identifier)s' does not respect TT-1 formatting rules.", identifier=doc_id))
        issue_dt = document.get('issue_datetime') or ''
        if not issue_dt:
            errors.append(_("Flow %(name)s is missing the issue datetime (TT-3).", name=flow.name))
        elif not self._is_valid_issue_datetime(issue_dt):
            errors.append(_("Issue datetime '%(value)s' must follow format 204 (AAAAMMJJHHMMSS).", value=issue_dt))

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
        if (flow.report_kind == 'transaction' and
                report_vals.get('expected_international_invoices') and
                not invoices and not flow.error_move_ids):
            errors.append(_("Flow %(name)s must contain at least one international invoice.", name=flow.name))

        for invoice in invoices:
            invoice_id = invoice.get('id') or _("Invoice without identifier")
            due_code = (invoice.get('tax_due_date_type_code') or '').strip()
            if not due_code:
                errors.append(_("Invoice %(invoice)s is missing the tax due date type code (TT-64).", invoice=invoice_id))
            elif not flow._is_valid_due_date_code(due_code):
                errors.append(_("Invoice %(invoice)s has an invalid tax due date type code '%(code)s'.", invoice=invoice_id, code=due_code))

            self._check_vat(invoice_id, invoice.get('seller') or {}, 'seller', errors)
            self._check_vat(invoice_id, invoice.get('buyer') or {}, 'buyer', errors)

            for note in invoice.get('notes') or []:
                subject = note.get('subject')
                if subject and subject not in self._valid_note_subjects():
                    errors.append(_("Invoice %(invoice)s references unsupported note subject '%(subject)s'.", invoice=invoice_id, subject=subject))

            if currency and invoice.get('currency') == currency.name:
                self._check_amounts(invoice_id, currency, invoice.get('monetary_total') or {}, ('tax_exclusive_amount', 'tax_amount'), errors)
                for subtotal in invoice.get('tax_subtotals') or []:
                    if subtotal.get('tax_percent') is None:
                        errors.append(_("Invoice %(invoice)s is missing a tax rate in its breakdown.", invoice=invoice_id))
                    self._check_amounts(invoice_id, currency, subtotal, ('taxable_amount', 'tax_amount'), errors)
                for allowance in invoice.get('allowance_charges') or []:
                    self._check_amounts(invoice_id, currency, allowance, ('amount',), errors)
                    if allowance.get('tax_percent') is None:
                        errors.append(_("Invoice %(invoice)s has an allowance/charge without a tax rate.", invoice=invoice_id))

    def _validate_summaries(self, report_vals, currency, errors):
        """Validate B2C summary entries."""
        flow = self.flow
        summaries = report_vals.get('transaction_summaries') or []
        if (flow.report_kind == 'transaction' and
                report_vals.get('expected_b2c_transactions') and
                not summaries and not flow.error_move_ids):
            errors.append(_("Flow %(name)s must include aggregated B2C data.", name=flow.name))

        for summary in summaries:
            due_code = (summary.get('tax_due_date_type_code') or '').strip()
            if due_code and not flow._is_valid_due_date_code(due_code):
                errors.append(_("B2C summary for %(date)s has an invalid tax due date type code '%(code)s'.", date=summary.get('date'), code=due_code))
            vat_breakdown = summary.get('vat_breakdown') or []
            if not vat_breakdown:
                errors.append(_("B2C summary for %(date)s is missing the VAT breakdown (TT-78).", date=summary.get('date')))
            if currency and summary.get('currency') == currency.name:
                self._check_amounts(summary.get('date'), currency, summary, ('tax_exclusive_amount', 'tax_total'), errors, summary=True)
                for vat_bucket in vat_breakdown:
                    if vat_bucket.get('vat_rate') is None:
                        errors.append(_("B2C summary for %(date)s is missing a VAT rate in the breakdown.", date=summary.get('date')))
                    self._check_amounts(summary.get('date'), currency, vat_bucket, ('amount_untaxed', 'amount_tax'), errors, summary=True)

    def _validate_payments(self, report_vals, currency, errors):
        """Validate payment entries."""
        if self.flow.report_kind != 'payment' or not currency:
            return
        payments = report_vals.get('invoice_payments') or report_vals.get('transaction_payments') or []
        for payment in payments:
            payment_currency = payment.get('currency')
            if payment_currency and payment_currency != currency.name:
                continue
            self._check_amounts(payment.get('id') or payment.get('date'), currency, payment, ('amount',), errors, payment=True)
            for subtotal in payment.get('subtotals') or []:
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

    def _is_valid_transmission_identifier(self, identifier):
        """Validate TT-1 transmission identifier format."""
        return bool(
            identifier and
            identifier.strip() == identifier and
            '  ' not in identifier and
            len(identifier) <= 50,
        )

    def _is_valid_issue_datetime(self, value):
        """Validate TT-3 issue datetime format (YYYYMMDDHHMMSS)."""
        if not value or len(value) != 14 or not value.isdigit():
            return False
        try:
            datetime.strptime(value, '%Y%m%d%H%M%S')
            return True
        except ValueError:
            return False

    def _valid_note_subjects(self):
        """Return set of valid note subject codes per spec."""
        return {'AAB', 'PMT', 'PRD', 'SUR'}

    def _digits(self, value):
        """Extract only digits from value."""
        return ''.join(ch for ch in (value or '') if ch.isdigit())

    def _filename(self, slice_date):
        """Generate payload filename."""
        filename = self.flow._build_filename()
        if slice_date:
            filename = filename.replace('.xml', f'_{slice_date}.xml')
        return filename
