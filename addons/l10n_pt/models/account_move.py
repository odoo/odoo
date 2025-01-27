import re
import urllib.parse
import stdnum.pt.nif

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import float_compare, float_repr, SQL

from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils

AT_SERIES_TYPE_SAFT_TYPE_MAP = {
    'out_invoice_ft': 'FT',
    'out_receipt_fr': 'FR',
    'out_invoice_fs': 'FS',
    'out_refund_nc': 'NC',
}

AT_SERIES_TYPE_MOVE_TYPE_MAP = {
    'out_invoice_ft': 'out_invoice',
    'out_receipt_fr': 'out_receipt',
    'out_invoice_fs': 'out_invoice',
    'out_refund_nc': 'out_refund',
}


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_pt_get_line_vat_exemptions_reasons(self):
        """
        Returns a string with the VAT exemption reason codes per line. E.g: [M16]
        It is added to the tax name in the invoice PDF to satisfy the following requirement by the PT tax authority:
        " In case the reason for exemption is not presented on the correspondent line, any other type of reference
        must be used allowing linking the exempted line to the correspondent reason."
        """
        self.ensure_one()
        return ", ".join(f"[{reason}]" for reason in sorted(set(
            self.tax_ids.filtered(lambda tax: tax.l10n_pt_tax_exemption_reason).mapped('l10n_pt_tax_exemption_reason')
        )))

class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_pt_qr_code_str = fields.Char(string='Portuguese QR Code', compute='_compute_l10n_pt_qr_code_str', store=True)
    l10n_pt_inalterable_hash_short = fields.Char(string='Short version of the Portuguese hash', compute='_compute_l10n_pt_inalterable_hash')
    l10n_pt_inalterable_hash_version = fields.Integer(string='Portuguese hash version', compute='_compute_l10n_pt_inalterable_hash')
    l10n_pt_atcud = fields.Char(string='Portuguese ATCUD', compute='_compute_l10n_pt_atcud', store=True)
    l10n_pt_show_future_date_warning = fields.Boolean(compute='_compute_l10n_pt_show_future_date_warning')
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
    l10n_pt_at_series_id = fields.Many2one("l10n_pt.at.series", string="Official Series of the Tax Authority", compute="_compute_l10n_pt_at_series_id")
    # Document type used in invoice template (when printed, documents have to present the document type on each page)
    l10n_pt_document_type = fields.Char(string="Portuguese Document Type", compute='_compute_l10n_pt_document_type')
    # Used for QR code string generation and when filling the SAF-T (PT)
    l10n_pt_document_type_code = fields.Char(string="Portuguese SAF-T Document Code", compute='_compute_l10n_pt_document_type_code', store=True)

    ####################################
    # OVERRIDES
    ####################################

    def action_reverse(self):
        for move in self.filtered(lambda m: m.company_id.account_fiscal_country_id.code == "PT"):
            if move.payment_state == 'reversed':
                raise UserError(_("You cannot reverse an invoice that has already been fully reversed."))
        return super().action_reverse()

    def action_post(self):
        for move in self.filtered(lambda m: m.company_id.account_fiscal_country_id.code == 'PT').sorted('invoice_date'):
            move._l10n_pt_check_dates()
            move._l10n_pt_check_move_line()
        return super().action_post()

    ####################################
    # MISC REQUIREMENTS
    ####################################

    def _get_starting_sequence(self):
        # EXTENDS account sequence.mixin
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_starting_sequence()
        if self.journal_id.type in ['sale', 'bank', 'cash']:
            starting_sequence = "%s%04d/00000" % (self.journal_id.code, self.date.year)
        else:
            starting_sequence = "%s%04d-%02d/0000" % (self.journal_id.code, self.date.year, self.date.month)
        if self.journal_id.refund_sequence and self.move_type in ('out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        if self.journal_id.payment_sequence and self.origin_payment_id:
            starting_sequence = "P" + starting_sequence
        return starting_sequence

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.company_id.account_fiscal_country_id.code == "PT":
            where_string += " AND move_type = %(move_type)s"
            param['move_type'] = self.move_type
        return where_string, param

    @api.constrains('name')
    def _check_name(self):
        for move in self.filtered(lambda m: (
            m.company_id.account_fiscal_country_id.code == 'PT'
            and m.is_sale_document(include_receipts=True)
            and m.name
            and m.name != '/'
        )):
            if not re.match(r'^[^/^ ]+/[0-9]+$', move.name):
                raise ValidationError(_(
                    "The name of the document (%s) is invalid. It must start with the identifier "
                    "of the series followed by a slash and the number of the document within the "
                    "series (e.g. INV2024/1).", move.name
                ))
            prefix = move.name.split("/")[0]
            at_series = self.env['l10n_pt.at.series'].search([('company_id', '=', move.company_id.id), ('prefix', '=', prefix)])
            if not at_series:
                raise ValidationError(_(
                    "The series %s has not yet been registered with an official AT code. "
                    "You can do so in the Accounting Settings.", prefix
                ))
            if AT_SERIES_TYPE_MOVE_TYPE_MAP[at_series.type] != move.move_type:
                raise UserError(_(
                    "The type %(series_type)s of the series %(prefix)s does not match the type of the document %(move_name)s (%(move_type)s).",
                    prefix=at_series.prefix,
                    series_type=dict(at_series._fields['type'].selection).get(at_series.type),
                    move_name=move.name,
                    move_type=dict(move._fields['move_type'].selection).get(move.move_type),
                ))

    @api.depends('state', 'invoice_date', 'company_id.account_fiscal_country_id.code')
    def _compute_l10n_pt_show_future_date_warning(self):
        """
        No other documents may be issued with the current or previous date within the same series as
        a document issued in the future. If user enters an invoice date ahead of current date,
        a warning will be displayed.
        """
        for move in self:
            move.l10n_pt_show_future_date_warning = (
                move.company_id.account_fiscal_country_id.code == 'PT'
                and move.state == 'draft'
                and move.invoice_date
                and move.invoice_date > fields.Date.today()
            )

    def _l10n_pt_check_dates(self):
        """
        According to the Portuguese tax authority:
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series"
        """
        self.ensure_one()
        self.env['account.move'].flush_model(['l10n_pt_hashed_on'])
        self.env.cr.execute(SQL("""
            SELECT
                MAX(CASE WHEN journal_id = %s AND move_type = %s THEN invoice_date ELSE NULL END) AS max_invoice_date,
                MAX(l10n_pt_hashed_on) AS max_hashed_on_date
            FROM account_move
            WHERE state = 'posted'
        """, self.journal_id.id, self.move_type))

        max_invoice_date, max_hashed_on_date = self.env.cr.fetchone()

        if max_invoice_date and max_invoice_date > fields.Date.today() and self.invoice_date < max_invoice_date:
            raise UserError(_("You cannot create an invoice with a date anterior to the last invoice issued within the same journal."))

        if max_hashed_on_date and max_hashed_on_date > fields.Datetime.now():
            raise UserError(_("There exists secured invoices with a lock date ahead of the present time."))

    def _l10n_pt_check_move_line(self):
        """
        According to the Portuguese tax authority:
        "The documents printed by the invoicing program must not present negative amounts."
        Regarding taxes, "The printing of documents where the transmission of goods or services is VAT exempted,
        must show the expression foreseen by law, granting exemption or the applicable legal cause." Therefore even
        0% taxes should be added to a line, with its corresponding exemption reason.
        """
        self.ensure_one()
        if self.move_type != 'entry' and not self.invoice_line_ids.tax_ids:
            raise UserError(_("You cannot create an invoice without VAT tax."))
        if (
            self.is_sale_document(include_receipts=True)
            and self.invoice_line_ids.filtered(lambda line: float_compare(line.price_total, 0.0, precision_rounding=self.currency_id.rounding) < 0)
        ):
            raise UserError(_("You cannot create an invoice with negative lines on it. Consider adding a discount percentage to the invoice line instead."))

    def _l10n_pt_get_vat_exemptions_reasons(self):
        self.ensure_one()
        return sorted(set(
            self.invoice_line_ids.tax_ids
                .filtered(lambda tax: tax.l10n_pt_tax_exemption_reason)
                .mapped(lambda tax: dict(tax._fields['l10n_pt_tax_exemption_reason'].selection).get(tax.l10n_pt_tax_exemption_reason))
        ))

    ####################################
    # HASH
    ####################################

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_integrity_hash_fields()
        return ['invoice_date', 'l10n_pt_hashed_on', 'amount_total', 'move_type', 'sequence_prefix', 'sequence_number']

    def _get_l10n_pt_document_number(self):
        """
        Uses the SAF-T (PT) document type and the move name to generate the document number. """
        self.ensure_one()
        at_series = self.env['l10n_pt.at.series'].search([('company_id', '=', self.company_id.id), ('prefix', '=', self.name.split("/")[0])])
        return f"{AT_SERIES_TYPE_SAFT_TYPE_MAP[at_series.type] if at_series else self.move_type} {self.name}"

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
            'gross_total': float_repr(move.amount_total, 2),
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
            ('state', '=', 'posted'),
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

    ####################################
    # ATCUD - AT SERIES - QR CODE
    ####################################

    @api.depends('inalterable_hash')
    def _compute_l10n_pt_at_series_id(self):
        for move in self:
            if move.inalterable_hash:
                move.l10n_pt_at_series_id = self.env['l10n_pt.at.series'].search([
                    ('company_id', '=', move.company_id.id),
                    ('prefix', '=', move.name.split("/")[0])
                ])
            else:
                move.l10n_pt_at_series_id = None

    @api.depends('l10n_pt_at_series_id')
    def _compute_l10n_pt_document_type(self):
        for move in self:
            if (
                move.company_id.account_fiscal_country_id.code == 'PT'
                and move.l10n_pt_at_series_id
            ):
                move.l10n_pt_document_type = dict(move.l10n_pt_at_series_id._fields['type'].selection).get(move.l10n_pt_at_series_id.type)
            else:
                move.l10n_pt_document_type = False

    @api.depends('l10n_pt_at_series_id')
    def _compute_l10n_pt_document_type_code(self):
        for move in self:
            if (
                move.company_id.account_fiscal_country_id.code == 'PT'
                and move.l10n_pt_at_series_id
            ):
                move.l10n_pt_document_type_code = AT_SERIES_TYPE_SAFT_TYPE_MAP[move.l10n_pt_at_series_id.type]
            else:
                move.l10n_pt_document_type_code = False

    @api.depends('l10n_pt_inalterable_hash_short')
    def _compute_l10n_pt_atcud(self):
        for move in self:
            if (
                move.company_id.account_fiscal_country_id.code == 'PT'
                and not move.l10n_pt_atcud
                and move.inalterable_hash
                and move.is_sale_document(include_receipts=True)
            ):
                move.l10n_pt_atcud = f"{move.l10n_pt_at_series_id._get_at_code()}-{move.sequence_number}"
            else:
                move.l10n_pt_atcud = False

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
            m.company_id.account_fiscal_country_id.code == "PT"
            and m.move_type in self.get_sale_types(include_receipts=True)
            and m.inalterable_hash
            and not m.l10n_pt_qr_code_str  # Skip if already computed
        )):
            if not move.company_id.vat or not stdnum.pt.nif.is_valid(move.company_id.vat):
                action = self.env.ref('base.action_res_company_form')
                raise RedirectWarning(_('Please define the VAT on your company (e.g. PT123456789)'), action.id, _('Company Settings'))

            details_by_tax_group = get_details_by_tax_category(move)

            pt_hash_utils.verify_prerequisites_qr_code(move, move.inalterable_hash, move.l10n_pt_atcud)
            # Most of the values needed to create the QR code string are filled in pt_hash_utils, also used by pt_pos and pt_stock
            qr_code_dict, tax_letter = pt_hash_utils.l10n_pt_common_qr_code_str(move, self.env, move.date)
            qr_code_dict['D:'] = f"{move.l10n_pt_document_type_code}*"
            qr_code_dict['G:'] = f"{move._get_l10n_pt_document_number()}*"
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
