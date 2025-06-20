import re
import urllib.parse

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import SQL, float_repr

from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils
from odoo.addons.l10n_pt.models.l10n_pt_at_series import AT_SERIES_ACCOUNTING_DOCUMENT_TYPES

AT_SERIES_TYPE_SAFT_TYPE_MAP = {
    'out_invoice': 'FT',
    'out_receipt': 'FS',
    'out_refund': 'NC',
    'debit_note': 'ND',
}


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_pt_line_discount = fields.Float(string="Line Discount", digits='Discount', default=0.0)
    # PT does not accept negative lines, so global discounts need to be handled via a separate field at the account.move
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
        compute='_compute_discount',
        store=True,
    )

    @api.depends('move_id.l10n_pt_global_discount', 'l10n_pt_line_discount')
    def _compute_discount(self):
        """
        Compute the total discount considering both the line discount and the global discount.
        Ex: A line with unit price of 100, a line discount of 10% and a global discount of 10%.
        The total discount is 19%: 1 - (1 - 0.1) * (1 - 0.1) = 0.19
        """
        for line in self.filtered(lambda l: l.move_id.country_code == 'PT'):
            global_discount = (line.move_id.l10n_pt_global_discount or 0.0) / 100
            line_discount = (line.l10n_pt_line_discount or 0.0) / 100
            line.discount = (1 - (1 - global_discount) * (1 - line_discount)) * 100

    @api.constrains('l10n_pt_line_discount')
    def _check_l10n_pt_line_discount(self):
        # The PT tax authority also requires that discounts must be in the range between 0% and 100%.
        for line in self:
            if line.l10n_pt_line_discount < 0.0 or line.l10n_pt_line_discount > 100.0:
                raise ValidationError(_("Discount amounts should be between 0% and 100%."))

    @api.constrains('tax_ids')
    def _check_l10n_pt_tax_ids(self):
        if self.filtered(
            lambda l: l.display_type == 'product'
            and l.move_type != 'entry'
            and l.company_id.account_fiscal_country_id.code == 'PT'
            and not l.tax_ids
        ):
            raise ValidationError(_("You cannot create a move line without VAT tax."))

    @api.constrains('price_total')
    def _check_l10n_pt_negative_lines(self):
        if self.filtered(
            lambda l: l.display_type == 'product'
            and l.move_type != 'entry'
            and l.company_id.account_fiscal_country_id.code == 'PT'
            and l.price_total < 0.0
        ):
            raise ValidationError(_("You cannot create an invoice with negative lines on it. "
                                    "To add a discount, add a Line Discount or a Global Discount."))

    def _l10n_pt_get_line_vat_exemptions_reasons(self, as_string=True):
        """
        Returns a string with the VAT exemption reason codes per line. E.g: [M16]
        It is added to the tax name in the invoice PDF to satisfy the following requirement by the PT tax authority:
        "In case the reason for exemption is not presented on the correspondent line, any other type of reference
        must be used allowing linking the exempted line to the correspondent reason."
        """
        self.ensure_one()
        exemption_reasons = sorted(set(
            self.tax_ids.filtered(lambda tax: tax.l10n_pt_tax_exemption_reason)
            .mapped('l10n_pt_tax_exemption_reason')
        ))
        return ", ".join(f"[{reason}]" for reason in exemption_reasons) if as_string else exemption_reasons


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_pt_qr_code_str = fields.Char('Portuguese QR Code', compute='_compute_l10n_pt_qr_code_str', store=True)
    l10n_pt_inalterable_hash_short = fields.Char(
        'Short version of the Portuguese hash',
        compute='_compute_l10n_pt_inalterable_hash',
    )
    l10n_pt_inalterable_hash_version = fields.Integer(
        'Portuguese hash version',
        compute='_compute_l10n_pt_inalterable_hash',
    )
    l10n_pt_atcud = fields.Char(
        string='Portuguese ATCUD',
        compute='_compute_l10n_pt_atcud',
        store=True,
        help="Unique document code formed by the AT series validation code and the number of the document. "
             "Only assigned once the document is secured.",
    )
    l10n_pt_document_number = fields.Char(
        string="Unique Document Number",
        compute='_compute_l10n_pt_document_number',
        store=True,
        help="Internal identifier for Portuguese documents, made up of the document type code,"
             "the series name, and the number of the document within the series.",
    )
    l10n_pt_show_future_date_warning = fields.Boolean(compute='_compute_l10n_pt_show_future_date_warning')
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
    l10n_pt_at_series_id = fields.Many2one(
        comodel_name="l10n_pt.at.series",
        string="AT Series",
        compute='_compute_l10n_pt_at_series_id',
        readonly=False, store=True,
    )
    l10n_pt_at_series_line_id = fields.Many2one(
        comodel_name="l10n_pt.at.series.line",
        string="Document-specific AT Series",
        compute='_compute_l10n_pt_at_series_line_id',
    )
    # Document type used in invoice template (when printed, documents have to present the document type on each page)
    l10n_pt_document_type = fields.Selection(
        selection=AT_SERIES_ACCOUNTING_DOCUMENT_TYPES,
        string="Portuguese Document Type",
        compute='_compute_l10n_pt_document_type',
        store=True,
    )
    l10n_pt_print_version = fields.Selection(
        selection=[
            ('original', 'Original print'),
            ('reprint', 'Reprint'),
        ],
        string="Version of Printed Document",
        copy=False,
    )
    l10n_pt_cancel_reason = fields.Char(
        string="Reason for Cancellation",
        copy=False,
        readonly=True,
        help="Reason given by the user for cancelling this move",
    )
    l10n_pt_global_discount = fields.Float(
        string="Global Discount %",
        digits='Discount',
        inverse='_inverse_l10n_pt_global_discount',
    )

    ####################################
    # OVERRIDES
    ####################################

    def action_reverse(self):
        """
        Portuguese certification requirements: "The program must not allow the creation of credit notes regarding
        previously cancelled documents or already fully rectified."
        """
        if self.filtered(lambda m: m.country_code == "PT" and m.payment_state == 'reversed'):
            raise UserError(_("You cannot reverse an invoice that has already been fully reversed."))
        return super().action_reverse()

    def action_post(self):
        for move in self.filtered(lambda m: m.country_code == 'PT').sorted('invoice_date'):
            move._check_l10n_pt_at_series_id()
            move._check_l10n_pt_document_number()
            move._check_l10n_pt_dates()
            if move.move_type == 'out_refund' and move.reversed_entry_id:
                move._check_l10n_pt_refund_values()
        return super().action_post()

    def write(self, vals):
        for move in self:
            if move.state in ('posted', 'cancel') and 'l10n_pt_at_series_id' in vals:
                raise UserError(_("The AT Series of a posted account move cannot be changed."))
        return super().write(vals)

    def action_open_print_wizard(self):
        self.ensure_one()
        if (
            self.country_code == 'PT'
            and self.move_type in ('out_invoice', 'out_refund', 'out_receipt')
            and self.l10n_pt_print_version
        ):
            return {
                'name': _('Reprint Reason'),
                'type': 'ir.actions.act_window',
                'res_model': 'l10n_pt.reprint.reason',
                'view_mode': 'form',
                'target': 'new',
            }
        return self.action_print_pdf()

    @api.depends('state', 'l10n_pt_document_number')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        for move in self:
            # Documents with a l10n_pt_document_number can be directly cancelled, and are still part of the hash chain
            if move.l10n_pt_document_number:
                move.show_reset_to_draft_button = False

    @api.model
    def _get_move_hash_domain(self, common_domain=False, force_hash=False):
        # EXTENDS account to include cancelled moves
        domain = super()._get_move_hash_domain(common_domain, force_hash)
        if self.env.company.account_fiscal_country_id.code == 'PT':
            return [
                ('state', 'in', ('posted', 'cancel')) if condition == ('state', '=', 'posted') else condition
                for condition in domain
            ]
        return super()._get_move_hash_domain(common_domain, force_hash)

    def preview_invoice(self):
        self._l10n_pt_compute_missing_hashes()
        return super().preview_invoice()

    ####################################
    # MISC REQUIREMENTS
    ####################################

    @api.onchange('l10n_pt_global_discount')
    def _inverse_l10n_pt_global_discount(self):
        self.line_ids._conditional_add_to_compute('discount', lambda l: (l.move_id.is_invoice(True)))
        self.line_ids._conditional_add_to_compute('price_subtotal', lambda l: (l.move_id.is_invoice(True)))

    @api.constrains('l10n_pt_global_discount')
    def _check_l10n_pt_global_discount(self):
        for move in self.filtered(lambda m: m.country_code == 'PT'):
            if move.l10n_pt_global_discount < 0.0 or move.l10n_pt_global_discount > 100.0:
                raise ValidationError(_("Discount amounts should be between 0% and 100%."))

    def update_l10n_pt_print_version(self):
        self.ensure_one()
        if not self.l10n_pt_print_version:
            self.l10n_pt_print_version = 'original'
        else:
            self.l10n_pt_print_version = 'reprint'

    def _check_l10n_pt_document_number(self):
        for move in self.filtered(lambda m: (
            m.country_code == 'PT'
            and m.move_type in ('out_invoice', 'out_receipt', 'out_refund')
            and m.l10n_pt_at_series_id
        )):
            if not move.l10n_pt_at_series_line_id:
                action_error = {
                    'view_mode': 'form',
                    'name': _('AT Series'),
                    'res_model': 'l10n_pt.at.series',
                    'res_id': move.l10n_pt_at_series_id.id,
                    'type': 'ir.actions.act_window',
                    'views': [[self.env.ref('l10n_pt.view_l10n_pt_at_series_form').id, 'form']],
                    'target': 'new',
                }
                raise RedirectWarning(
                    _("There is no AT series for the document type %(move_type)s registered under the series name %(series_name)s. "
                      "Create a new series or view existing series via the Accounting Settings.",
                      move_type=dict(move._fields['l10n_pt_document_type'].selection).get(move.l10n_pt_document_type),
                      series_name=move.l10n_pt_at_series_id.name),
                    action_error,
                    _('Add an AT Series'),
                )
            if move.l10n_pt_document_number and not re.match(r'^[^ ]+ [^/^ ]+/[0-9]+$', move.l10n_pt_document_number):
                raise ValidationError(_(
                    "The document number (%s) is invalid. It must start with the internal code "
                    "of the document type, a space, the name of the series followed by a slash and the number of the "
                    "document within the series (e.g. INV 2025A/1). Please check if the series selected fulfill these "
                    "requirements.", move.l10n_pt_document_number
                ))

    @api.depends('state', 'invoice_date', 'country_code')
    def _compute_l10n_pt_show_future_date_warning(self):
        """
        No other documents may be issued with the current or previous date within the same series as
        a document issued in the future. If user enters an invoice date ahead of current date,
        a warning will be displayed.
        """
        for move in self:
            move.l10n_pt_show_future_date_warning = (
                move.country_code == 'PT'
                and move.state == 'draft'
                and move.is_sale_document(include_receipts=True)
                and move.invoice_date
                and move.invoice_date > fields.Date.today()
            )

    def _check_l10n_pt_dates(self):
        """
        According to the Portuguese tax authority:
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series"
        """
        self.ensure_one()
        self.env['account.move'].flush_model(['l10n_pt_hashed_on'])
        self.env.cr.execute(SQL("""
            SELECT MAX(invoice_date) AS max_invoice_date,
                   MAX(l10n_pt_hashed_on) AS max_hashed_on_date
              FROM account_move
             WHERE state = ANY(ARRAY['posted', 'cancel'])
               AND l10n_pt_at_series_id IS NOT NULL AND l10n_pt_at_series_id = %s
               AND move_type = %s
        """, self.l10n_pt_at_series_id.id or SQL('NULL'), self.move_type))

        max_invoice_date, max_hashed_on_date = self.env.cr.fetchone()

        if (
            max_invoice_date
            and max_invoice_date > fields.Date.today()
            and (self.invoice_date or fields.Date.context_today(self)) < max_invoice_date
        ):
            raise UserError(_("You cannot create an invoice with a date earlier than the date of the last "
                              "invoice issued in this AT series."))

        if max_hashed_on_date and max_hashed_on_date > fields.Datetime.now():
            raise UserError(_("There exists secured invoices with a lock date ahead of the present time."))

    def _check_l10n_pt_refund_values(self):
        """
        The PT certification requires that credit notes, line by line and in total, do not have
        bigger values than the original invoice.
        """
        self.ensure_one()
        if len(self.invoice_line_ids) > len(self.reversed_entry_id.invoice_line_ids):
            raise UserError(_("The reversal of a move should not have more lines than the original move."))
        for index in range(len(self.invoice_line_ids)):
            if self.invoice_line_ids[index].price_total > self.reversed_entry_id.invoice_line_ids[index].price_total:
                raise UserError(_("The value or quantity per line of a reversal cannot exceed the "
                                  "value or quantity of the original line."))

    def _l10n_pt_get_vat_exemptions_reasons(self):
        self.ensure_one()
        exemption_selection = dict(self.env['account.tax']._fields['l10n_pt_tax_exemption_reason'].selection)
        exemption_reasons = set()
        for line in self.invoice_line_ids:
            for reason_code in line._l10n_pt_get_line_vat_exemptions_reasons(as_string=False):
                exemption_reasons.add(exemption_selection.get(reason_code))
        return sorted(exemption_reasons)

    ####################################
    # PT FIELDS - ATCUD, AT SERIES
    ####################################

    def _check_l10n_pt_at_series_id(self):
        self.ensure_one()
        if self.move_type in ('out_invoice', 'out_receipt', 'out_refund'):
            if not self.l10n_pt_at_series_id:
                raise UserError(_("Please select a series for this move."))
            if not self.l10n_pt_at_series_id.active:
                raise UserError(_("An inactive series cannot be used."))

    @api.depends('move_type', 'company_id', 'date', 'journal_id')
    def _compute_l10n_pt_at_series_id(self):
        moves = self.filtered(
            lambda m: m.move_type in AT_SERIES_TYPE_SAFT_TYPE_MAP and m.journal_id
            and not (m.l10n_pt_at_series_id and m.l10n_pt_at_series_id.sale_journal_id == m.journal_id)
        )
        moves_by_key = {}
        for move in moves:
            # Group moves of the same company, journal and move_type
            moves_by_key.setdefault((move.company_id.id, move.journal_id.id, move.move_type), []).append(move)
        for key, moves in moves_by_key.items():
            company_id, journal_id, move_type = key
            # Get the last move with an AT series for each group
            last_move = self.env['account.move'].search([
                ('company_id', '=', company_id),
                ('journal_id', '=', journal_id),
                ('move_type', '=', move_type),
                ('l10n_pt_at_series_id', '!=', False),
            ], order='id desc', limit=1)
            # If no AT series used in a move in this journal, fallback to an active series for this journal
            at_series = last_move.l10n_pt_at_series_id or self.env['l10n_pt.at.series'].search([
                ('company_id', '=', company_id),
                ('active', '=', True),
                ('sale_journal_id', '=', journal_id),
            ], limit=1)

            for move in moves:
                move.l10n_pt_at_series_id = at_series

    @api.depends('l10n_pt_at_series_id')
    def _compute_l10n_pt_at_series_line_id(self):
        for (document_type, series), moves in self.grouped(lambda m: (m.l10n_pt_document_type, m.l10n_pt_at_series_id)).items():
            moves.l10n_pt_at_series_line_id = series._get_line_for_type(document_type) if series else None

    @api.depends('l10n_pt_at_series_id', 'l10n_pt_at_series_line_id', 'move_type', 'company_id', 'state')
    def _compute_l10n_pt_document_number(self):
        for move in self:
            if (
                move.country_code == 'PT'
                and move.move_type in ('out_invoice', 'out_receipt', 'out_refund')
                and move.l10n_pt_at_series_line_id
            ):
                if move.state == 'posted' and not move.l10n_pt_document_number:
                    move.l10n_pt_document_number = move.l10n_pt_at_series_line_id._l10n_pt_get_document_number_sequence().next_by_id()
            else:
                move.l10n_pt_document_number = False

    @api.depends('move_type')
    def _compute_l10n_pt_document_type(self):
        for move in self:
            if (
                move.country_code == 'PT'
                and move.move_type in ('out_invoice', 'out_refund', 'out_receipt')
            ):
                if 'debit_origin_id' in self.env['account.move']._fields and move.debit_origin_id:
                    move.l10n_pt_document_type = 'debit_note'
                else:
                    move.l10n_pt_document_type = move.move_type
            else:
                move.l10n_pt_document_type = False

    @api.depends('l10n_pt_inalterable_hash_short', 'l10n_pt_document_number', 'move_type')
    def _compute_l10n_pt_atcud(self):
        for move in self:
            if (
                move.country_code == 'PT'
                and not move.l10n_pt_atcud
                and move.inalterable_hash
                and move.move_type in ('out_invoice', 'out_refund', 'out_receipt')
                and move.l10n_pt_document_number
            ):
                current_seq_number = int(move.l10n_pt_document_number.split('/')[-1])
                move.l10n_pt_atcud = f"{move.l10n_pt_at_series_line_id._get_at_code()}-{current_seq_number}"
            else:
                move.l10n_pt_atcud = move.l10n_pt_atcud or False

    ####################################
    # HASH AND QR CODE
    ####################################

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_integrity_hash_fields()
        return ['invoice_date', 'l10n_pt_hashed_on', 'amount_total_signed', 'move_type', 'name', 'l10n_pt_document_number']

    def _get_l10n_pt_document_number(self):
        """ Allows patching in tests """
        self.ensure_one()
        return self.l10n_pt_document_number

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
            'name': move._get_l10n_pt_document_number(),
            # As per PT requirements for signature: "In case the document is issued in a foreign currency, the amount
            # must be the counter value in EUR, once this will be the amount exported on the SAF-T (PT) file."
            'gross_total': float_repr(abs(move.amount_total_signed), 2),
            'previous_signature': previous_hash,
        } for move in self]
        return pt_hash_utils.sign_records(self.env, docs_to_sign, 'account.move')

    def _get_max_system_date(self):
        self.env['account.move'].flush_model(['l10n_pt_hashed_on'])
        self.env.cr.execute(SQL("""
            SELECT
                MAX(l10n_pt_hashed_on) AS max_hashed_on_date
            FROM account_move
        """))
        return self.env.cr.fetchone()[0]

    @api.model
    def _l10n_pt_compute_missing_hashes(self):
        """
        Compute the hash for all records that do not have one yet
        """
        all_moves = self.sudo().search([
            ('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt')),
            ('state', 'in', ('posted', 'cancel')),
            ('l10n_pt_document_number', '!=', False),
            ('inalterable_hash', '=', False),
            ('company_id', 'child_of', self.env.company.root_id.id),
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
                move.l10n_pt_inalterable_hash_short = False

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
            m.country_code == "PT"
            and m.move_type in ('out_invoice', 'out_refund', 'out_receipt')
            and m.inalterable_hash
            and not m.l10n_pt_qr_code_str  # Skip if already computed
        )):
            details_by_tax_group = get_details_by_tax_category(move)

            pt_hash_utils.verify_prerequisites_qr_code(move, move.inalterable_hash, move.l10n_pt_atcud)
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
