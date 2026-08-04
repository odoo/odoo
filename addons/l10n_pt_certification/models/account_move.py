import json
import re
import urllib.parse

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import float_repr

from odoo.addons.l10n_pt_certification.const import (
    PT_SIMPLIFIED_INVOICE_GOODS_LIMIT,
    PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT,
)
from odoo.addons.l10n_pt_certification.models.l10n_pt_at_series import (
    AT_SERIES_ACCOUNTING_DOCUMENT_TYPES,
)
from odoo.addons.l10n_pt_certification.models.l10n_pt_document_mixin import (
    L10N_PT_DOCUMENT_NUMBER_RE,
)
from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils

AT_SERIES_TYPE_SAFT_TYPE_MAP = {
    'out_invoice': 'FT',
    'out_receipt': 'FS',
    'out_invoice_receipt': 'FR',
    'out_refund': 'NC',
    'debit_note': 'ND',
}


class AccountMoveLine(models.Model):
    _name = 'account.move.line'
    _inherit = ['account.move.line', 'l10n.pt.priced.line.mixin']

    def _l10n_pt_get_document(self):
        self.ensure_one()
        return self.move_id

    @api.constrains('price_total')
    def _check_l10n_pt_zero_negative_lines(self):
        """ Lines with a total amount <= 0 are not allowed, according to PT requirements """
        if non_positive_lines := self.filtered(
            lambda l: l.display_type == 'product'
            and l.move_type != 'entry'
            and l.company_id.account_fiscal_country_id.code == 'PT'
            and (l.price_total <= 0.0 and not l.is_downpayment)
        ):
            if any(line.price_total < 0.0 for line in non_positive_lines):
                raise ValidationError(self.env._("You cannot create an invoice with negative lines on it. "
                                        "To add a discount, add a Line Discount or a Global Discount."))
            else:
                raise ValidationError(self.env._("Invoice lines with an amount of 0 are not allowed."))


class AccountMove(models.Model):
    _name = "account.move"
    # `l10n.pt.document.mixin` carries the numbering & identity layer (AT series, document number,
    # ATCUD, print version). The signing layer is deliberately not mixed in: moves keep riding the
    # base `account` hashing framework (`inalterable_hash`) rather than `l10n_pt_inalterable_hash`.
    _inherit = ["account.move", "l10n.pt.document.mixin", "l10n.pt.priced.document.mixin"]

    _l10n_pt_date_field = "invoice_date"
    _l10n_pt_document_type_depends = ('move_type',)

    # PT Document Mixin Fields
    l10n_pt_document_type = fields.Selection(selection_add=AT_SERIES_ACCOUNTING_DOCUMENT_TYPES)
    l10n_pt_at_series_id = fields.Many2one(
        comodel_name="l10n_pt.at.series",
        string="AT Series",
        compute='_compute_l10n_pt_at_series_id',
        readonly=False, store=True, copy=False,
        domain="[('journal_id', '=', journal_id)]",
    )

    # PT Hashing & QR Fields
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
    l10n_pt_inalterable_hash_short = fields.Char(
        string='Short version of the Portuguese hash',
        compute='_compute_l10n_pt_inalterable_hash',
    )
    l10n_pt_inalterable_hash_version = fields.Integer(
        string='Portuguese hash version',
        compute='_compute_l10n_pt_inalterable_hash',
    )
    l10n_pt_qr_code_str = fields.Char('Portuguese QR Code', compute='_compute_l10n_pt_qr_code_str', store=True)

    ####################################
    # PT DOCUMENT MIXINS HOOKS
    ####################################

    def _l10n_pt_country_ok(self):
        self.ensure_one()
        return self.country_code == 'PT' and self.move_type in AT_SERIES_TYPE_SAFT_TYPE_MAP

    def _l10n_pt_get_document_date(self):
        self.ensure_one()
        return self.invoice_date or self.date or fields.Date.context_today(self)

    def _l10n_pt_get_document_type(self):
        self.ensure_one()
        if 'debit_origin_id' in self._fields and self.debit_origin_id:
            return 'debit_note'
        return self.move_type

    def _l10n_pt_get_lines(self):
        self.ensure_one()
        return self.invoice_line_ids

    def _l10n_pt_assign_document_number(self, number):
        # For a PT invoice the move name IS the legal document number.
        super()._l10n_pt_assign_document_number(number)
        self.name = number

    ####################################
    # OVERRIDES
    ####################################

    def write(self, vals):
        # Since the AT Series defines the document number, it cannot be changed to avoid holes in the
        # document number sequence.
        for move in self:
            if move.state in ('posted', 'cancel') and 'l10n_pt_at_series_id' in vals:
                raise UserError(self.env._("The AT Series of a posted document cannot be changed."))
        return super().write(vals)

    @api.depends('state', 'l10n_pt_document_number')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        for move in self:
            # Documents with a l10n_pt_document_number can be directly cancelled, and are still part of the hash chain
            if move.l10n_pt_document_number:
                move.show_reset_to_draft_button = False

    def button_draft(self):
        """Cannot reset to draft an invoice with a document number"""
        if not self.env.context.get('_pt_button_cancel') and self.filtered(lambda m: m.country_code == "PT" and m.l10n_pt_document_number):
            raise UserError(self.env._("You cannot reset to draft a Portuguese certified document with a document number."))
        return super().button_draft()

    def button_cancel(self):
        """Cannot cancel an already reversed or cancelled invoice"""
        if self.filtered(lambda m: m.country_code == "PT" and (m.payment_state == 'reversed' or m.state == 'cancel')):
            raise UserError(self.env._("You cannot cancel an invoice that has already been fully reversed or cancelled."))
        return super(AccountMove, self.with_context(_pt_button_cancel=True)).button_cancel()

    def action_reverse(self):
        """Cannot reverse an already reversed or cancelled invoice"""
        if self.filtered(lambda m: m.country_code == "PT" and (m.payment_state == 'reversed' or m.state == 'cancel')):
            raise UserError(self.env._("You cannot reverse an invoice that has already been fully reversed or cancelled."))
        return super().action_reverse()

    def _refunds_origin_required(self):
        if self.country_code == 'PT':
            return True
        return super()._refunds_origin_required()

    @api.model
    def _get_move_hash_domain(self, common_domain=False, force_hash=False):
        # EXTENDS account to include cancelled moves
        domain = super()._get_move_hash_domain(common_domain, force_hash)
        if self.env.company.account_fiscal_country_id.code == 'PT':
            return domain.map_conditions(
                lambda condition: Domain('state', 'in', ('posted', 'cancel'))
                if (condition.field_expr, condition.operator, condition.value) == ('state', '=', 'posted')
                else condition
            )
        return domain

    def button_hash(self):
        for move in self:
            if move.l10n_pt_at_series_missing_at_code:
                raise UserError(self.env._(
                    "The AT Series '%(series)s' is missing the AT Validation Code. "
                    "Please register the series with the Autoridade Tributária before sending or printing.",
                    series=move.l10n_pt_at_series_id.display_name,
                ))
        return super().button_hash()

    def preview_invoice(self):
        """
        PT requirement: "No document in a preparatory or preview state may be printed prior to its
        completion and signing".
        """
        self._l10n_pt_compute_missing_hashes()
        return super().preview_invoice()

    def _l10n_pt_get_invoice_legal_document(self, filetype, allow_fallback=False):
        """
        For Portugal, we store the binaries of both the invoice's original and reprint versions.
        If they exist, the appropriate binary will be used to render the file. Else, generate the file.
        """
        filename = f"{self._get_move_display_name().replace(' ', '_').replace('/', '_')}.pdf"
        content, report_type = self.env['ir.actions.report'].with_company(self.company_id) \
            ._pre_render_qweb_pdf('account.report_invoice_with_payments', self.ids)
        content_by_id = self.env['ir.actions.report']._get_splitted_report(
            'account.report_invoice_with_payments', content, report_type
        )
        return {
            'filename': filename,
            'filetype': 'pdf',
            'content': content_by_id[self.id],
        }

    def _get_invoice_legal_documents(self, filetype, allow_fallback=False):
        # EXTENDS account
        self.ensure_one()
        if self.country_code == 'PT':
            return self._l10n_pt_get_invoice_legal_document(filetype, allow_fallback=allow_fallback)
        return super()._get_invoice_legal_documents(filetype, allow_fallback=allow_fallback)

    def _get_invoice_legal_documents_all(self, allow_fallback=False):
        # EXTENDS account
        self.ensure_one()
        if self.country_code == 'PT':
            return [self._l10n_pt_get_invoice_legal_document('pdf', allow_fallback=allow_fallback)]
        return super()._get_invoice_legal_documents_all(allow_fallback=allow_fallback)

    def action_print_pdf(self):
        """ PT requirement: documents being reprinted require a reprint reason """
        self.ensure_one()
        # If document is reprint and does not yet have a reason, call reprint reason wizard. Else, proceed with print
        if (
            self._l10n_pt_country_ok()
            and self.l10n_pt_print_version
            and not self.env.context.get('has_reprint_reason')
        ):
            return self.action_open_reprint_wizard('action_print_pdf')
        return super().action_print_pdf()

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        if pt_moves := self.filtered(lambda m: m.country_code == 'PT'):
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', pt_moves._name),
                ('res_id', 'in', pt_moves.ids),
                ('res_field', '=', binary_field),
            ])
            move_vals = {att.res_id: att for att in attachments}
            for move in pt_moves:
                move[attachment_field] = move_vals.get(move._origin.id, False)
        super(AccountMove, self - pt_moves)._compute_linked_attachment_id(attachment_field, binary_field)

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self._l10n_pt_country_ok():
            return 'l10n_pt_certification.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_starting_sequence(self):
        self.ensure_one()
        if self._l10n_pt_country_ok():
            if self.l10n_pt_at_series_id:
                return f"{self.l10n_pt_at_series_id.document_identifier}/00000"
            standard = super()._get_starting_sequence()
            if self.l10n_pt_document_type == 'out_receipt':
                standard = 'S' + standard
            elif self.l10n_pt_document_type == 'out_invoice_receipt':
                standard = 'REC' + standard
            if re.match(r'^[A-Z0-9]+/\d.+/\d+$', standard):  # "INV/2026/00000" → "INV 2026/00000"
                return standard.replace('/', ' ', 1)
            return standard
        return super()._get_starting_sequence()

    def _post(self, soft=True):
        pt_moves = self.filtered(lambda m: m._l10n_pt_country_ok()).sorted('invoice_date')
        for move in pt_moves:
            if not move.journal_id:
                raise UserError(self.env._("You cannot post an invoice without a journal. Please select a journal and try again."))

            move._check_l10n_pt_simplified_invoice_limit()
            if move._l10n_pt_is_invoice_receipt():
                move.l10n_pt_document_type = 'out_invoice_receipt'

            if not move.l10n_pt_at_series_id:
                move.l10n_pt_at_series_id = move._l10n_pt_create_at_series_from_sequence()

            move._check_l10n_pt_lines_taxes()
            move._check_l10n_pt_at_series_id()

        pt_moves._check_l10n_pt_dates()
        pt_moves._set_l10n_pt_document_number()
        pt_moves._check_l10n_pt_reversal()
        return super()._post(soft)

    ####################################
    # CHECKS
    ####################################

    @api.onchange('name')
    def _onchange_l10n_pt_name(self):
        if self._l10n_pt_country_ok() and self.name and not re.match(L10N_PT_DOCUMENT_NUMBER_RE, self.name):
            raise ValidationError(self.env._(
                "The document number (%s) is invalid. It must start with the internal code of the document type, "
                "a space, the name of the series followed by a single slash and the number of the "
                "document within the series (e.g. INV 2025A/1).",
                self.name
            ))

    def _check_l10n_pt_simplified_invoice_limit(self):
        """
        A sales receipt is a simplified invoice (FS). Per the Portuguese VAT code, simplified invoices
        cannot exceed 1000 EUR for goods or 100 EUR for services. An over-limit receipt cannot be posted.
        """
        self.ensure_one()
        if not self._l10n_pt_country_ok() or self.move_type != 'out_receipt':
            return

        total_amount_in_eur = self.currency_id._convert(
            self.amount_total,
            self.env.ref('base.EUR'),
            self.company_id,
            self.invoice_date or fields.Date.context_today(self)
        )
        # If product has no type or its tax has no tax_scope, it is considered a service to be safe
        has_services = any(
            (
                line.product_id.type == 'service'
                or line.tax_ids.filtered(lambda t: t.tax_scope == 'service')
                or (
                    not line.product_id.type
                    and not line.tax_ids.filtered(lambda t: t.tax_scope)
                )
            )
            for line in self.invoice_line_ids
            if line.display_type == 'product'
        )
        limit = PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT if has_services else PT_SIMPLIFIED_INVOICE_GOODS_LIMIT
        if total_amount_in_eur > limit:
            raise UserError(self.env._(
                "A sales receipt (simplified invoice) cannot exceed %(limit)s EUR. "
                "Please issue a regular invoice instead.",
                limit=float_repr(limit, 2),
            ))

    def _l10n_pt_is_invoice_receipt(self):
        self.ensure_one()
        if not self._l10n_pt_country_ok() or self.move_type != 'out_invoice':
            return False
        if self.payment_state == 'paid':
            return True
        payments = self.matched_payment_ids.filtered(
            lambda p: p.state in ('in_process', 'paid') and p.payment_type == 'inbound'
        )
        if not payments:
            return False
        total_paid = sum(
            payment.currency_id._convert(
                payment.amount,
                self.currency_id,
                self.company_id,
                payment.date or self.invoice_date or fields.Date.context_today(self),
            )
            for payment in payments
        )
        return self.currency_id.compare_amounts(total_paid, self.amount_total) >= 0

    def _check_l10n_pt_reversal(self):
        pt_moves = self.filtered(lambda m: m._l10n_pt_country_ok())
        if any(m.move_type == 'out_refund' and not m.reversed_entry_id for m in pt_moves):
            raise UserError(self.env._("You cannot post a credit note without referencing the original invoice."))
        pt_moves._check_reversal_amounts_and_quantities(only_reconciled=False)

    def action_open_reprint_wizard(self, action_to_return=None):
        action = self.env.ref('l10n_pt_certification.action_open_reprint_wizard').read()[0]
        action['context'] = dict(action_to_return=action_to_return, **json.loads(action.get('context', {})))
        return action

    ####################################
    # PT FIELDS - ATCUD, AT SERIES
    ####################################

    def _l10n_pt_create_at_series_from_sequence(self):
        """ Auto-create an AT series based on the move's sequence prefix and date metadata.
        This is called when no matching AT series exists for a new sequence period.

        :return: The newly created l10n_pt.at.series record, or an empty recordset if creation fails.
        """
        self.ensure_one()

        if (self.name and self.name != '/'):
            seq_source = self.name
        else:
            seq_source = self._get_starting_sequence()

        _, format_values = self._get_sequence_format_param(seq_source)

        prefix1 = format_values.get('prefix1', '')
        prefix = re.sub(r'[^a-zA-Z0-9]', '', prefix1.strip())

        sequence_number_reset = self._deduce_sequence_number_reset(seq_source)
        date_start, date_end, forced_year_start, forced_year_end = self._get_sequence_date_range(sequence_number_reset)

        year = forced_year_start or format_values.get('year') or date_start.year
        year_end = forced_year_end or format_values.get('year_end') or ''

        month = str(format_values.get('month', '00')).zfill(2)

        if sequence_number_reset == 'month':
            series_name = f"{year}{month}"
        elif sequence_number_reset == 'year_range_month':
            series_name = f"{year}{year_end}{month}"
        elif sequence_number_reset == 'year_range':
            series_name = f"{year}{year_end}"
        elif sequence_number_reset == 'year':
            series_name = str(year)
        else:
            series_name = f"{prefix}{year}"

        suffix_key_map = {
            'year': 'prefix2',
            'month': 'prefix3',
            'year_range': 'prefix3',
            'year_range_month': 'prefix4',
        }
        if suffix_key := suffix_key_map.get(sequence_number_reset):
            raw_suffix = format_values.get(suffix_key, '') or ''
            alpha_suffix = re.sub(r'[^a-zA-Z]', '', raw_suffix)
            series_name = f"{series_name}{alpha_suffix}"

        return self.env['l10n_pt.at.series'].create({
            'name': series_name,
            'prefix': prefix,
            'document_type': self.l10n_pt_document_type,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'date_start': date_start,
            'date_end': date_end,
        })

    @api.depends('move_type', 'l10n_pt_document_type', 'invoice_date', 'journal_id', 'company_id')
    def _compute_l10n_pt_at_series_id(self):
        # Do not recompute AT series if move already has one and journal of AT series matches the move journal
        today = fields.Date.today()
        at_series_model = self.env['l10n_pt.at.series']
        moves_to_compute = self.filtered(
            lambda m: (
                m._l10n_pt_country_ok()
                and m.journal_id
                and (
                    not m.l10n_pt_at_series_id
                    or m.l10n_pt_at_series_id.journal_id != m.journal_id
                    or m.l10n_pt_at_series_id.document_type != m.l10n_pt_document_type
                    or not m.l10n_pt_at_series_id.active
                    or not m.l10n_pt_at_series_id._l10n_pt_is_valid_on(m.invoice_date or today)
                )
            )
        )
        for move in moves_to_compute:
            # Get the last move with an AT series for this journal and document type
            last_move = self.env['account.move'].search([
                ('id', '!=', move.id),
                ('company_id', '=', move.company_id.id),
                ('journal_id', '=', move.journal_id.id),
                ('l10n_pt_document_type', '=', move.l10n_pt_document_type),
                ('l10n_pt_at_series_id', '!=', False),
                ('l10n_pt_at_series_id.active', '=', True),
                *at_series_model._l10n_pt_validity_domain(
                    move.invoice_date or today, prefix='l10n_pt_at_series_id.',
                ),
            ], order='id desc', limit=1)
            # If no AT series used in a move in this journal, fallback to an active series for this journal
            at_series = last_move.l10n_pt_at_series_id or at_series_model.search([
                *at_series_model._l10n_pt_company_domain(move.company_id),
                *at_series_model._l10n_pt_validity_domain(move.invoice_date or today),
                ('journal_id', '=', move.journal_id.id),
                ('document_type', '=', move.l10n_pt_document_type),
                ('active', '=', True),
            ], limit=1)

            move.l10n_pt_at_series_id = at_series

    ####################################
    # HASH AND QR CODE
    ####################################

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_integrity_hash_fields()
        return ['invoice_date', 'l10n_pt_hashed_on', 'amount_total_signed', 'move_type', 'name', 'l10n_pt_document_number']

    def _calculate_hashes(self, previous_hash=None):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._calculate_hashes(previous_hash=previous_hash)
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        self.l10n_pt_hashed_on = fields.Datetime.now()
        docs_to_sign = [{
            'id': move.id,
            'sorting_key': move.sequence_number,
            'date': move.date.isoformat(),
            'system_entry_date': move.l10n_pt_hashed_on.isoformat(timespec='seconds'),
            'name': move._l10n_pt_get_document_number(),
            # As per PT requirements for signature: "In case the document is issued in a foreign currency, the amount
            # must be the counter value in EUR, once this will be the amount exported on the SAF-T (PT) file."
            'gross_total': float_repr(abs(move.amount_total_signed), 2),
            'previous_signature': previous_hash,
        } for move in self]
        return pt_hash_utils.sign_records(self.env, docs_to_sign, 'account.move')

    @api.model
    def _l10n_pt_compute_missing_hashes(self):
        """
        Compute the hash for all records that do not have one yet
        """
        all_moves = self.sudo().search([
            ('move_type', 'in', self.get_sale_types(include_receipts=True)),
            ('state', 'in', ('posted', 'cancel')),
            ('l10n_pt_document_number', '!=', False),
            ('inalterable_hash', '=', False),
            ('country_code', '=', 'PT'),
            ('company_id', 'child_of', self.env.companies.root_id.ids),
        ], order='sequence_prefix,sequence_number')
        all_moves.button_hash()

    @api.depends('inalterable_hash')
    def _compute_l10n_pt_inalterable_hash(self):
        for move in self:
            if move.inalterable_hash:
                hash_version, hash_str = move.inalterable_hash.split("$")[1:]
                move.l10n_pt_inalterable_hash_version = int(hash_version)
                move.l10n_pt_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                move.l10n_pt_inalterable_hash_version = False
                move.l10n_pt_inalterable_hash_short = False

    def l10n_pt_verify_prerequisites_qr_code(self):
        self.ensure_one()
        if self._l10n_pt_country_ok():
            return pt_hash_utils.verify_prerequisites_qr_code(self, self.inalterable_hash, self.l10n_pt_atcud)
        return None

    @api.depends('l10n_pt_atcud')
    def _compute_l10n_pt_qr_code_str(self):
        """
        Generate the informational QR code for Portugal invoicing.
        E.g.: A:509445535*B:123456823*C:BE*D:FT*E:N*F:20220103*G:FT 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """

        def format_amount(account_move, amount):
            """
            Convert amount to EUR based on the rate of a given account_move's date
            Format amount to 2 decimals as per SAF-T (PT) requirements
            """
            amount_eur = account_move.currency_id._convert(amount, self.env.ref('base.EUR'), account_move.company_id, account_move.date)
            return float_repr(amount_eur, 2)

        def get_details_by_tax_category(account_move):
            """
            :return: {tax_category : {'base': base, 'vat': vat}}
            """
            res = {}
            tax_groups = account_move.tax_totals['subtotals'][0]['tax_groups']

            for group in tax_groups:
                tax_group = self.env['account.tax.group'].browse(group['id'])
                if (
                    tax_group.l10n_pt_tax_region == 'PT-ALL'  # I.e. tax is valid in all regions (PT, PT-AC, PT-MA)
                    or (
                        tax_group.l10n_pt_tax_region
                        and tax_group.l10n_pt_tax_region == account_move.company_id.l10n_pt_region_code
                    )
                ):
                    res[tax_group.l10n_pt_tax_category] = {
                        'base': format_amount(account_move, group['base_amount']),
                        'vat': format_amount(account_move, group['tax_amount']),
                    }
            return res

        for move in self.filtered(lambda m: (
            m._l10n_pt_country_ok()
            and m.inalterable_hash
            and not m.l10n_pt_qr_code_str  # Skip if already computed
        )):
            details_by_tax_group = get_details_by_tax_category(move)

            move.l10n_pt_verify_prerequisites_qr_code()
            # Most of the values needed to create the QR code string are filled in pt_hash_utils, also used by pt_pos and pt_stock
            qr_code_dict, tax_letter = pt_hash_utils.l10n_pt_common_qr_code_str(move, self.env, move.date)
            qr_code_dict['D:'] = f"{AT_SERIES_TYPE_SAFT_TYPE_MAP[move.l10n_pt_document_type]}*"
            qr_code_dict['H:'] = f"{move.l10n_pt_atcud}*"
            if details_by_tax_group.get('E'):
                qr_code_dict[f'{tax_letter}2:'] = f"{details_by_tax_group.get('E')['base']}*"
            for i, tax_category in enumerate(('R', 'I', 'N')):
                if details_by_tax_group.get(tax_category):
                    qr_code_dict[f'{tax_letter}{i * 2 + 3}:'] = f"{details_by_tax_group.get(tax_category)['base']}*"
                    qr_code_dict[f'{tax_letter}{i * 2 + 4}:'] = f"{details_by_tax_group.get(tax_category)['vat']}*"
            qr_code_dict['N:'] = f"{format_amount(move, move.tax_totals['tax_amount'])}*"
            qr_code_dict['O:'] = f"{format_amount(move, move.tax_totals['total_amount'])}*"
            qr_code_dict['Q:'] = f"{move.l10n_pt_inalterable_hash_short}*"
            # Create QR code string from dictionary
            qr_code_str = ''.join(f"{key}{value}" for key, value in sorted(qr_code_dict.items()))
            move.l10n_pt_qr_code_str = urllib.parse.quote_plus(qr_code_str)
