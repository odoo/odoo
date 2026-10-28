import re

from stdnum.pt import nif

from odoo import api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import float_repr
from odoo.tools.misc import format_date

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

    @api.model_create_multi
    def create(self, vals_list):
        given_vals_list = [dict(vals) for vals in vals_list]
        lines = super().create(vals_list)
        lines._l10n_pt_keep_given_discounts(given_vals_list)
        return lines

    def _reconcile_plan(self, reconciliation_plan):
        # EXTENDS account
        # A PT invoice is paid, or settled by a credit note or an outstanding payment, only once it is
        # issued: the receipt and the SAF-T (PT) reference its document number.
        def flatten(plan):
            for item in plan:
                if isinstance(item, (list, tuple)):
                    yield from flatten(item)
                else:
                    yield item

        amls = self.browse().union(*flatten(reconciliation_plan))
        amls.move_id.filtered(lambda m: m.move_type in ('out_invoice', 'out_receipt'))._l10n_pt_check_issued(
            self.env._("A payment or reconciliation"),
        )
        return super()._reconcile_plan(reconciliation_plan)

    @api.constrains('price_total')
    def _check_l10n_pt_zero_negative_lines(self):
        """
        Lines with a total amount <= 0 are not allowed on a PT document, according to PT requirements. The
        documents a PT company receives (vendor bills and refunds) are not PT documents: they are
        recorded as their issuer made them.
        """
        if non_positive_lines := self.filtered(
            lambda l: l.display_type == 'product'
            and l.move_id._l10n_pt_country_ok()
            and (l.price_total <= 0.0 and not l.is_downpayment)
        ):
            if any(line.price_total < 0.0 for line in non_positive_lines):
                raise ValidationError(self.env._("You cannot create an invoice with negative lines on it. "
                                        "To add a discount, add a Line Discount or a Global Discount."))
            else:
                raise ValidationError(self.env._("Invoice lines with an amount of 0 are not allowed."))


class AccountMove(models.Model):
    _name = "account.move"
    # `l10n.pt.qr.document.mixin` brings the QR code and, through its own `_inherit`, the numbering
    # & identity layer (AT series, document number, ATCUD, print version). The signing layer is
    # deliberately not mixed in: moves keep riding the base `account` hashing framework
    # (`inalterable_hash`) rather than `l10n_pt_inalterable_hash`, which is why the QR layer
    # addresses the signature through `_l10n_pt_hash_field` instead of naming a field.
    _inherit = ["account.move", "l10n.pt.qr.document.mixin", "l10n.pt.priced.document.mixin"]

    _l10n_pt_date_field = "invoice_date"
    _l10n_pt_hash_field = "inalterable_hash"
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
    # Indexed for the latest SystemEntryDate, read before issuing any document (`_l10n_pt_check_system_clock`).
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True, index='btree_not_null')

    # The reason given when reversing a document, exported in the SAF-T (PT) References of the credit note.
    l10n_pt_reversal_reason = fields.Char(string="Reversal Reason", readonly=True, copy=False)

    # What the SAF-T (PT) will need and the draft does not have yet.
    l10n_pt_saft_missing_data = fields.Text(compute='_compute_l10n_pt_saft_missing_data')

    @api.depends(
        'state', 'move_type', 'company_id.vat', 'company_id.zip',
        'invoice_line_ids.display_type', 'invoice_line_ids.product_id.default_code', 'invoice_line_ids.product_id.name',
        'invoice_line_ids.tax_ids.amount', 'invoice_line_ids.tax_ids.l10n_pt_tax_exemption_reason',
    )
    def _compute_l10n_pt_saft_missing_data(self):
        """
        Alert, while the document can still change, to the data the SAF-T (PT) requires and the draft
        lacks (Despacho 8632/2014 3.4.1). Once issued, the export reports it, or refuses to run. A
        product-less line is not listed: posting refuses it (D-4, `_check_l10n_pt_lines_products`).
        """
        for move in self:
            issues = []
            if move.state == 'draft' and move._l10n_pt_country_ok():
                lines = move._l10n_pt_get_lines()
                if no_reference := lines.product_id.filtered(lambda product: not product.default_code):
                    issues.append(self.env._(
                        "These products have no Internal Reference: %(products)s.",
                        products=", ".join(no_reference.mapped('display_name')),
                    ))
                if short_name := lines.product_id.filtered(lambda product: len(product.name or '') < 2):
                    issues.append(self.env._(
                        "These products need a name of two characters at least: %(products)s.",
                        products=", ".join(short_name.mapped('display_name')),
                    ))
                if no_reason := lines.tax_ids.filtered(lambda tax: tax._l10n_pt_lacks_exemption_reason()):
                    issues.append(self.env._(
                        "These taxes charge nothing and have no VAT exemption reason: %(taxes)s.",
                        taxes=", ".join(no_reason.mapped('name')),
                    ))
                company = move.company_id
                if not company.vat or not nif.is_valid(company.vat):
                    issues.append(self.env._("The company's VAT is missing or invalid: it should read like PT123456789."))
                if company.zip and not re.match(r"[0-9]{4}-[0-9]{3}", company.zip):
                    issues.append(self.env._("The company's postal code should read like 1234-789."))
            move.l10n_pt_saft_missing_data = "\n".join(issues) or False

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
        # Sections and notes are not priced lines: they carry no tax, discount or exemption reason.
        return self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')

    def _l10n_pt_get_saft_doc_type(self):
        self.ensure_one()
        return AT_SERIES_TYPE_SAFT_TYPE_MAP[self.l10n_pt_document_type]

    def _l10n_pt_qr_rate_date(self):
        # The `O:` amount must equal the gross total that was signed, `amount_total_signed`, which core
        # converts at the rate of the invoice date, else of the accounting date
        # (`account.move.line._compute_currency_rate`). Converting at another date would make the
        # printed total disagree with the signature.
        self.ensure_one()
        return self.invoice_date or self.date

    def _l10n_pt_qr_get_totals(self):
        self.ensure_one()
        return (
            self._l10n_pt_qr_format_amount(self.tax_totals['tax_amount_currency']),
            self._l10n_pt_qr_format_amount(self.tax_totals['total_amount_currency']),
        )

    def _l10n_pt_get_tax_details_by_region(self):
        return self._l10n_pt_split_not_subject_bases(super()._l10n_pt_get_tax_details_by_region())

    def _l10n_pt_get_gross_total(self):
        # As per PT requirements for signature: "In case the document is issued in a foreign
        # currency, the amount must be the counter value in EUR, once this will be the amount
        # exported on the SAF-T (PT) file." `amount_total_signed` is that counter value.
        self.ensure_one()
        return abs(self.amount_total_signed)

    def _l10n_pt_assign_document_number(self, number):
        # An invoice takes its number in its series when posted, as its name, and keeps it through a
        # reset to draft. It becomes its document number when the invoice is issued (`_l10n_pt_issue`).
        self.ensure_one()
        self.name = number

    def _l10n_pt_is_numbered(self):
        # EXTENDS l10n_pt_certification (mixin)
        # Posting takes the number (`posted_before`), issuing the invoice gives it its document number.
        return super()._l10n_pt_is_numbered() or bool(self.posted_before and self.l10n_pt_at_series_id)

    @api.model
    def _l10n_pt_numbered_domain(self):
        # EXTENDS l10n_pt_certification (mixin)
        return super()._l10n_pt_numbered_domain() | (Domain('posted_before', '=', True) & Domain('l10n_pt_at_series_id', '!=', False))

    ####################################
    # OVERRIDES
    ####################################

    def write(self, vals):
        # Since the AT Series defines the document number, it cannot be changed to avoid holes in the
        # document number sequence.
        for move in self:
            if (
                'l10n_pt_at_series_id' in vals
                and move.l10n_pt_at_series_id.id != vals['l10n_pt_at_series_id']
                and (move.state in ('posted', 'cancel') or move._l10n_pt_is_numbered())
            ):
                raise UserError(self.env._("The AT Series of a posted document cannot be changed."))
        # The name of a PT invoice is the number it took in its series: changing it would leave a gap,
        # except through the resequencing of invoices not issued yet (`account.resequence.wizard`).
        if 'name' in vals and not self.env.context.get('l10n_pt_resequence') and self.filtered(lambda m: (
            m._l10n_pt_country_ok() and m._l10n_pt_is_numbered() and m.name != vals['name']
        )):
            raise UserError(self.env._("The number of a Portuguese invoice is taken in its AT series and cannot be changed."))
        # The delivery date is exported as the document's TaxPointDate (see `_compute_show_delivery_date`).
        if 'delivery_date' in vals and self.filtered(lambda m: (
            m.l10n_pt_document_number
            and m.country_code == 'PT'
            and m.delivery_date != fields.Date.to_date(vals['delivery_date'])
        )):
            raise UserError(self.env._("The delivery date of an issued Portuguese document cannot be changed."))
        return super().write(vals)

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        # The date the goods were made available or the services performed is recorded on the
        # document, to fill the SAF-T (PT) TaxPointDate (Despacho 8632/2014 3.2.12).
        super()._compute_show_delivery_date()
        for move in self.filtered(lambda m: m.country_code == 'PT'):
            move.show_delivery_date = move.is_sale_document()

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
        """
        Cannot cancel an already reversed or cancelled invoice. An invoice that took its number is
        annulled, not discarded: it is issued, cancelled, so that its series keeps no gap and the
        SAF-T (PT) reports it.
        """
        pt_moves = self.filtered(lambda m: m.country_code == "PT")
        if pt_moves.filtered(lambda m: m.payment_state == 'reversed' or m.state == 'cancel'):
            raise UserError(self.env._("You cannot cancel an invoice that has already been fully reversed or cancelled."))
        # A document rectified by a credit or debit note, even partially, is annulled only once that
        # note is (Despacho 8632/2014 3.3.8). Debit notes exist only with `account_debit_note`.
        rectifying = pt_moves.reversal_move_ids
        if 'debit_note_ids' in self._fields:
            rectifying |= pt_moves.debit_note_ids
        if rectifying := rectifying.filtered(lambda m: m.state == 'posted'):
            raise UserError(self.env._(
                "You cannot cancel an invoice while a credit or debit note rectifies it. Cancel %(notes)s first.",
                notes=", ".join(rectifying.mapped('name')),
            ))
        # Annulling goes through a transient draft, which core refuses for a signed move. An issued
        # PT invoice is signed and stays in its chain once cancelled, so let it through.
        res = super(AccountMove, self.with_context(_pt_button_cancel=True, allow_draft_hashed_entries=True)).button_cancel()
        cancelled = pt_moves.filtered(lambda m: m.state == 'cancel')
        cancelled._l10n_pt_issue()
        cancelled._l10n_pt_record_cancellation()
        return res

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
            domain = domain.map_conditions(
                lambda condition: Domain('state', 'in', ('posted', 'cancel'))
                if (condition.field_expr, condition.operator, condition.value) == ('state', '=', 'posted')
                else condition
            )
            # An invoice is signed when it is issued (`_l10n_pt_issue`), not when it is posted.
            return domain & (
                Domain('l10n_pt_document_number', '!=', False)
                | Domain('move_type', 'not in', self.get_sale_types(include_receipts=True))
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
        completion and signing". Previewing an invoice generates it: it issues it.
        """
        self._l10n_pt_issue()
        return super().preview_invoice()

    def _l10n_pt_get_invoice_legal_document(self, filetype, allow_fallback=False):
        """
        For Portugal, we store the binaries of both the invoice's original and reprint versions.
        If they exist, the appropriate binary will be used to render the file. Else, generate the file.
        """
        filename = f"{self._get_move_display_name().replace(' ', '_').replace('/', '_')}.pdf"
        if self.env.context.get('l10n_pt_legal_document_exists_only'):
            # Only checking that the document exists (see `get_extra_print_items`): don't render it.
            return {'filename': filename, 'filetype': 'pdf', 'content': None}
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

    def get_extra_print_items(self):
        # EXTENDS account
        # Core only checks whether each move has a document, to offer "Export ZIP". Skip rendering
        # the PT PDF for that check: it is slow and would count as a print of the document.
        return super(AccountMove, self.with_context(l10n_pt_legal_document_exists_only=True)).get_extra_print_items()

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
        """
        Posting a PT invoice takes the next number of its AT series, as its name; it does not issue
        it. The invoice is issued, i.e. given its document number and signed, when it is first
        generated for the customer (`_l10n_pt_issue`). An invoice reset to draft keeps its number,
        type and series, and is posted again under them.
        """
        today = fields.Date.context_today(self)
        pt_moves = self.filtered(lambda m: m._l10n_pt_country_ok()).sorted('invoice_date')
        # A soft post leaves future-dated moves in draft (see super): they take no number yet.
        to_number = pt_moves.filtered(lambda m: not m._l10n_pt_is_numbered() and not (soft and m.date > today))
        for move in pt_moves:
            if not move.journal_id:
                raise UserError(self.env._("You cannot post an invoice without a journal. Please select a journal and try again."))

            move._check_l10n_pt_simplified_invoice_limit()
            if move in to_number:
                if move._l10n_pt_is_invoice_receipt():
                    move.l10n_pt_document_type = 'out_invoice_receipt'
                if not move.l10n_pt_at_series_id:
                    # A series created since the move was computed (e.g. from the warning below) is picked up here.
                    move._compute_l10n_pt_at_series_id()
            if not move.l10n_pt_at_series_id:
                raise move._l10n_pt_missing_at_series_warning()

            move._check_l10n_pt_lines_taxes()
            move._check_l10n_pt_lines_products()
            move._check_l10n_pt_at_series_id()

        pt_moves._check_l10n_pt_dates()
        to_number._l10n_pt_take_series_numbers()
        pt_moves._check_l10n_pt_reversal()
        posted = super()._post(soft)
        if self.env.context.get('l10n_pt_issue_automatically'):
            posted._l10n_pt_issue()
        return posted

    def _l10n_pt_issue(self):
        """
        Issue the PT invoices of ``self`` that took their number but are not issued yet: their name
        becomes their document number, and they are signed (FAQ R23, Despacho 8632/2014 2.1.1).

        An invoice is issued when it is first generated for the customer -- printed, sent, previewed,
        downloaded, handed out by the PoS -- or when it is annulled, not when it is posted. In each
        series, invoices are issued in the order of their numbers (`_l10n_pt_check_series_continuity`).
        Issuing needs the signing service.
        """
        to_issue = self.filtered(lambda m: (
            m.state in ('posted', 'cancel')
            and m._l10n_pt_country_ok()
            and not m.l10n_pt_document_number
            and m._l10n_pt_is_numbered()
        ))
        if not to_issue:
            return
        to_issue._l10n_pt_check_series_continuity()
        to_issue.company_id._l10n_pt_check_company_vat()
        to_issue.company_id._l10n_pt_check_system_clock()
        # sudo: generating an invoice issues it, whoever generates it (a salesperson printing it, a
        # cron sending it); the issuing user is still recorded as the current one.
        to_issue_sudo = to_issue.sudo()
        for move in to_issue_sudo:
            move.l10n_pt_document_number = move.name
        to_issue_sudo._l10n_pt_record_issue()
        to_issue_sudo._check_l10n_pt_document_number()
        # The hash domain is the active company's (`_get_move_hash_domain`): sign in each invoice's own.
        for company, moves in to_issue_sudo.grouped('company_id').items():
            moves.with_company(company).button_hash()
        if unsigned := to_issue.filtered(lambda m: not m.inalterable_hash):
            raise UserError(self.env._("These invoices could not be signed: %s", ", ".join(unsigned.mapped('name'))))

    def _l10n_pt_issue_with_predecessors(self):
        """
        Issue the PT invoices of ``self``, and first the invoices before them in their AT series that
        are posted or cancelled but not issued yet: they are signed, as the chain of signatures needs,
        rather than blocking ``self`` (`_l10n_pt_check_series_continuity`). An invoice reset to draft
        keeps its number but cannot be issued: it still blocks the invoices after it.
        """
        to_issue = self.filtered(lambda m: (
            m._l10n_pt_country_ok() and not m.l10n_pt_document_number and m.l10n_pt_at_series_id
        ))
        if not to_issue:
            return
        # sudo: a series shared across branches holds invoices of companies the user may not see.
        predecessors = self.env['account.move'].sudo().search(
            Domain.OR(
                Domain('l10n_pt_at_series_id', '=', at_series.id)
                & Domain('sequence_number', '<', max(moves.mapped('sequence_number')))
                for at_series, moves in to_issue.grouped('l10n_pt_at_series_id').items()
            )
            & self._l10n_pt_numbered_domain()
            & Domain('state', 'in', ('posted', 'cancel'))
            & Domain('l10n_pt_document_number', '=', False),
        )
        (self.sudo() | predecessors)._l10n_pt_issue()

    def _l10n_pt_check_series_continuity(self):
        """
        Refuse to issue the invoices of ``self`` while a lower number of their series is not issued:
        the signature of a document chains to that of the previous one, and a series has no gap
        (Despacho 8632/2014 1.6, 2.2.1).
        """
        # sudo: a series shared across branches holds invoices of companies the user may not see.
        moves_sudo = self.env['account.move'].sudo()
        last_issued_numbers = dict(moves_sudo._read_group(
            [('l10n_pt_at_series_id', 'in', self.l10n_pt_at_series_id.ids), ('l10n_pt_document_number', '!=', False)],
            groupby=['l10n_pt_at_series_id'],
            aggregates=['sequence_number:max'],
        ))
        missing_by_series = {}
        for at_series, moves in self.grouped('l10n_pt_at_series_id').items():
            numbers = set(moves.mapped('sequence_number'))
            first_missing = (last_issued_numbers.get(at_series) or 0) + 1
            if missing := set(range(first_missing, max(numbers))) - numbers:
                missing_by_series[at_series] = missing
        if not missing_by_series:
            return
        waiting = moves_sudo.search([
            ('l10n_pt_at_series_id', 'in', [series.id for series in missing_by_series]),
            *self._l10n_pt_numbered_domain(),
            ('l10n_pt_document_number', '=', False),
            ('sequence_number', 'in', list(set().union(*missing_by_series.values()))),
        ], order='sequence_number')
        messages = []
        for at_series, missing in missing_by_series.items():
            series_waiting = waiting.filtered(lambda m: m.l10n_pt_at_series_id == at_series and m.sequence_number in missing)
            if series_waiting:
                messages.append(self.env._(
                    "Issue %(invoices)s first: the invoices of a series are issued in the order of their numbers.",
                    invoices=", ".join(series_waiting.mapped('name')),
                ))
            if lost := missing - set(series_waiting.mapped('sequence_number')):
                messages.append(self.env._(
                    "The AT series %(series)s has a gap: no invoice holds the numbers %(numbers)s. "
                    "Resequence the invoices not issued yet that follow them to close it.",
                    series=at_series.document_identifier,
                    numbers=", ".join(str(number) for number in sorted(lost)),
                ))
        raise UserError("\n".join(messages))

    def _l10n_pt_check_issued(self, document):
        """
        Refuse ``document`` (e.g. "A credit note"), which needs the PT invoices of ``self`` to be
        issued, while one is not. Flows that hand the invoice out at once (``l10n_pt_issue_automatically``,
        the PoS and online payments) issue it instead.
        """
        unissued = self.filtered(lambda m: m._l10n_pt_country_ok() and not m.l10n_pt_document_number)
        if unissued and self.env.context.get('l10n_pt_issue_automatically'):
            unissued._l10n_pt_issue()
            unissued = unissued.filtered(lambda m: not m.l10n_pt_document_number)
        if unissued:
            raise UserError(self.env._(
                "%(document)s needs these invoices to be issued first: %(invoices)s. "
                "An invoice is issued when it is first printed, sent or previewed.",
                document=document,
                invoices=", ".join(unissued.mapped('display_name')),
            ))

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

    def _check_l10n_pt_dates(self):
        # EXTENDS l10n_pt_certification (mixin)
        # An invoice reset to draft after posting keeps its number: its date stays between those of
        # the invoices numbered right before and after it in its series.
        renumbered = self.filtered(lambda m: m._l10n_pt_country_ok() and m.l10n_pt_at_series_id and m._l10n_pt_is_numbered())
        super(AccountMove, self - renumbered)._check_l10n_pt_dates()
        if not renumbered:
            return
        # sudo: the series' chronology covers every invoice it holds, whatever the user may see.
        neighbours = self.sudo().search([
            ('l10n_pt_at_series_id', 'in', renumbered.l10n_pt_at_series_id.ids),
            *self._l10n_pt_numbered_domain(),
            ('sequence_number', 'in', list({
                number for move in renumbered for number in (move.sequence_number - 1, move.sequence_number + 1)
            })),
        ])
        dates = {(m.l10n_pt_at_series_id, m.sequence_number): m._l10n_pt_get_document_date() for m in neighbours}
        for move in renumbered:
            date = move._l10n_pt_get_document_date()
            previous_date = dates.get((move.l10n_pt_at_series_id, move.sequence_number - 1))
            next_date = dates.get((move.l10n_pt_at_series_id, move.sequence_number + 1))
            if (previous_date and date < previous_date) or (next_date and date > next_date):
                raise UserError(self.env._(
                    "%(invoice)s keeps its number in the AT series %(series)s: its date must stay between "
                    "those of the invoices numbered right before and after it (%(previous)s, %(next)s).",
                    invoice=move.name,
                    series=move.l10n_pt_at_series_id.display_name,
                    previous=previous_date and format_date(self.env, previous_date) or "-",
                    next=next_date and format_date(self.env, next_date) or "-",
                ))

    def _check_l10n_pt_lines_products(self):
        """
        A PT sales document cannot be issued with a line without product: the SAF-T (PT) needs a
        ProductCode on every line, and once issued the document can no longer be corrected (D-4).
        """
        self.ensure_one()
        if not self._l10n_pt_country_ok():
            return
        if lines := self._l10n_pt_get_lines().filtered(lambda line: not line.product_id):
            raise UserError(self.env._(
                "Every line of a Portuguese invoice needs a product, which the SAF-T (PT) exports as its "
                "product code. Set one on these lines: %(lines)s",
                lines=", ".join(lines.mapped(lambda line: line.name or '/')),
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
        limit = self._l10n_pt_simplified_invoice_limit(self._l10n_pt_get_lines())
        if total_amount_in_eur > limit:
            raise UserError(self.env._(
                "A sales receipt (simplified invoice) cannot exceed %(limit)s EUR. "
                "Please issue a regular invoice instead.",
                limit=float_repr(limit, 2),
            ))

    @api.model
    def _l10n_pt_simplified_invoice_limit(self, lines):
        """
        The EUR limit of a simplified invoice for ``lines`` (any records with ``product_id`` and
        ``tax_ids``): 1000 for goods, 100 as soon as a service is involved (CIVA art. 40(1)).
        """
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
            for line in lines
        )
        return PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT if has_services else PT_SIMPLIFIED_INVOICE_GOODS_LIMIT

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
        # A credit or debit note references the document number of the invoice it rectifies.
        pt_moves.filtered(lambda m: m.move_type == 'out_refund').reversed_entry_id._l10n_pt_check_issued(
            self.env._("A credit note"),
        )
        if 'debit_origin_id' in self._fields:
            pt_moves.debit_origin_id._l10n_pt_check_issued(self.env._("A debit note"))
        pt_moves._check_reversal_amounts_and_quantities(only_reconciled=False)

    def action_open_reprint_wizard(self, action_to_return=None):
        action = self.env['ir.actions.act_window']._for_xml_id('l10n_pt_certification.action_open_reprint_wizard')
        action['context'] = {'action_to_return': action_to_return}
        return action

    ####################################
    # PT FIELDS - ATCUD, AT SERIES
    ####################################

    def _l10n_pt_missing_at_series_warning(self):
        """
        The warning raised when posting a move that has no AT series: it opens the series form,
        prefilled from the move's sequence. A series is never created on the fly, since a document
        may only be issued once the series is communicated to the AT and holds its validation code.
        """
        self.ensure_one()
        vals = self._l10n_pt_prepare_at_series_vals()
        document_type_name = dict(self._fields['l10n_pt_document_type']._description_selection(self.env)).get(vals['document_type'])
        return RedirectWarning(
            self.env._(
                "There is no AT series for %(document_type)s in the journal %(journal)s on %(date)s. "
                "Create it, and communicate it to the AT, before issuing this document.",
                document_type=document_type_name,
                journal=self.journal_id.display_name,
                date=fields.Date.to_string(self._l10n_pt_get_document_date()),
            ),
            {
                'name': self.env._('New AT Series'),
                'type': 'ir.actions.act_window',
                'res_model': 'l10n_pt.at.series',
                'view_mode': 'form',
                'views': [(self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_form').id, 'form')],
                'context': {
                    'l10n_pt_series_document_types': [vals['document_type']],
                    **{f'default_{field}': value for field, value in vals.items()},
                },
                'target': 'new',
            },
            self.env._('Create the AT Series'),
        )

    def _l10n_pt_prepare_at_series_vals(self):
        """ The values of the AT series this move would need, derived from its sequence prefix and date metadata. """
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

        vals = {
            'name': series_name,
            'prefix': prefix,
            'document_type': self.l10n_pt_document_type,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'date_start': fields.Date.to_string(date_start),
            'date_end': fields.Date.to_string(date_end) if date_end else False,
        }
        # A series name identifies it per document type (whatever its case) and per prefix within the
        # company, whatever its journal: another journal's series of the same year would collide, so
        # take the journal code. Proposed the same way to the user (the missing series warning) and
        # to the PoS (`_l10n_pt_create_at_series`).
        # sudo: a clash with any series of the company counts, ended or not, whatever the user may read.
        if self.env['l10n_pt.at.series'].sudo().with_context(active_test=False).search_count([
            ('company_id', '=', vals['company_id']),
            ('name', '=ilike', vals['name']),
            '|', ('document_type', '=', vals['document_type']), ('prefix', '=', vals['prefix']),
        ], limit=1):
            vals['name'] = re.sub(r'[^a-zA-Z0-9]', '', self.journal_id.code).upper() + vals['name']
        return vals

    @api.model
    def _l10n_pt_find_at_series(self, company, journal, document_type, date):
        """ An active AT series of ``journal`` for ``document_type``, valid on ``date``. """
        at_series_model = self.env['l10n_pt.at.series']
        return at_series_model.search([
            *at_series_model._l10n_pt_company_domain(company),
            *at_series_model._l10n_pt_validity_domain(date),
            ('journal_id', '=', journal.id),
            ('document_type', '=', document_type),
            ('active', '=', True),
        ], limit=1)

    @api.model
    def _l10n_pt_create_at_series(self, journal, document_type, date):
        """
        Create the AT series ``journal`` needs for ``document_type`` on ``date``, with the values the
        prefilled series form proposes. Creating a series registers it with the AT when the company's
        webservice is configured; otherwise it has no validation code yet, and numbering refuses it.

        The series is created as superuser, for callers whose users cannot create series themselves
        (the PoS); it is returned in the caller's environment.
        """
        draft = self.new({
            'move_type': 'out_invoice' if document_type == 'out_invoice_receipt' else document_type,
            'journal_id': journal.id,
            'company_id': journal.company_id.id,
            'date': date,
            'invoice_date': date,
        })
        draft.l10n_pt_document_type = document_type
        draft.l10n_pt_at_series_id = False
        draft.name = '/'
        return self.env['l10n_pt.at.series'].sudo().create(draft._l10n_pt_prepare_at_series_vals()).sudo(False)

    @api.depends('move_type', 'l10n_pt_document_type', 'invoice_date', 'journal_id', 'company_id')
    def _compute_l10n_pt_at_series_id(self):
        # Do not recompute AT series if move already has one and journal of AT series matches the move journal
        today = fields.Date.today()
        at_series_model = self.env['l10n_pt.at.series']
        moves_to_compute = self.filtered(
            lambda m: (
                m._l10n_pt_country_ok()
                and m.journal_id
                # An invoice that took its number keeps its series, also back in draft.
                and not m._l10n_pt_is_numbered()
                and (
                    not m.l10n_pt_at_series_id
                    or m.l10n_pt_at_series_id.journal_id != m.journal_id
                    or m.l10n_pt_at_series_id.document_type != m.l10n_pt_document_type
                    or not m.l10n_pt_at_series_id.active
                    or not m.l10n_pt_at_series_id._l10n_pt_is_valid_on(m.invoice_date or today)
                )
            )
        )
        for (company, journal, document_type, date), moves in moves_to_compute.grouped(
            lambda m: (m.company_id, m.journal_id, m.l10n_pt_document_type, m.invoice_date or today)
        ).items():
            # Get the last move with an AT series for this journal and document type
            last_move = self.env['account.move'].search([
                ('id', 'not in', moves._origin.ids),
                ('company_id', '=', company.id),
                ('journal_id', '=', journal.id),
                ('l10n_pt_document_type', '=', document_type),
                ('l10n_pt_at_series_id', '!=', False),
                ('l10n_pt_at_series_id.active', '=', True),
                *at_series_model._l10n_pt_validity_domain(date, prefix='l10n_pt_at_series_id.'),
            ], order='id desc', limit=1)
            # If no AT series used in a move in this journal, fallback to an active series for this journal
            moves.l10n_pt_at_series_id = last_move.l10n_pt_at_series_id or self._l10n_pt_find_at_series(
                company, journal, document_type, date,
            )

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
        # Core chains the full hash ($version$signature); the signature is chained bare.
        return self._l10n_pt_sign(previous_hash.split("$")[2] if previous_hash else "")

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
