import re
import urllib.parse
import stdnum.pt.nif

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import float_repr, format_date

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER
from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_pt_qr_code_str = fields.Char(string='Portuguese QR Code', compute='_compute_l10n_pt_qr_code_str', store=True)
    l10n_pt_inalterable_hash_short = fields.Char(string='Short version of the Portuguese hash', compute='_compute_l10n_pt_inalterable_hash')
    l10n_pt_inalterable_hash_version = fields.Integer(string='Portuguese hash version', compute='_compute_l10n_pt_inalterable_hash')
    l10n_pt_atcud = fields.Char(string='Portuguese ATCUD', compute='_compute_l10n_pt_atcud', store=True)
    l10n_pt_show_future_date_warning = fields.Boolean(compute='_compute_l10n_pt_show_future_date_warning')
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)

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
            move._l10n_pt_check_invoice_date()
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
        if self.journal_id.payment_sequence and self.payment_id:
            starting_sequence = "P" + starting_sequence
        return starting_sequence

    @api.constrains('name')
    def _check_name(self):
        for move in self.filtered(lambda m: (
            m.company_id.account_fiscal_country_id.code == 'PT'
            and m.journal_id.restrict_mode_hash_table
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
            if at_series.type != move.move_type:
                raise UserError(_(
                    "The type of the series %(prefix)s (%(series_type)s) does not match the type of the document %(move_name)s (%(move_type)s).",
                    prefix=at_series.prefix,
                    series_type=dict(at_series._fields['type'].selection).get(at_series.type),
                    move_name=move.name,
                    move_type=dict(move._fields['move_type'].selection).get(move.move_type),
                ))

    @api.depends('state', 'invoice_date', 'company_id.account_fiscal_country_id.code')
    def _compute_l10n_pt_show_future_date_warning(self):
        for move in self:
            move.l10n_pt_show_future_date_warning = (
                move.company_id.account_fiscal_country_id.code == 'PT'
                and move.state == 'draft'
                and move.invoice_date
                and move.invoice_date > fields.Date.today()
            )

    def _l10n_pt_check_invoice_date(self):
        """
        According to the Portuguese tax authority:
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series"
        """
        self.ensure_one()
        if not self.invoice_date:
            return
        self._cr.execute("""
            SELECT MAX(invoice_date)
              FROM account_move
             WHERE journal_id = %s
               AND move_type = %s
               AND state = 'posted'
        """, (self.journal_id.id, self.move_type))
        max_invoice_date = self._cr.fetchone()
        if max_invoice_date and max_invoice_date[0] and max_invoice_date[0] > fields.Date.today() and self.invoice_date < max_invoice_date[0]:
            raise UserError(_("You cannot create an invoice with a date anterior to the last invoice issued within the same journal."))

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
        self.ensure_one()
        return f"{self.move_type} {self.name}"

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
        return pt_hash_utils.sign_records(self.env, docs_to_sign)

    @api.model
    def _l10n_pt_compute_missing_hashes(self):
        """
        Compute the hash for all records that do not have one yet
        """
        pt_companies = self.env['res.company'].sudo().search([('account_fiscal_country_id.code', '=', 'PT')])
        for company in pt_companies:
            all_moves = self.sudo().search([
                ('restrict_mode_hash_table', '=', True),
                ('state', '=', 'posted'),
                ('inalterable_hash', '=', False),
                ('company_id', '=', company.id),
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
    # ATCUD - QR CODE
    ####################################

    @api.depends('l10n_pt_inalterable_hash_short')
    def _compute_l10n_pt_atcud(self):
        for move in self:
            if (
                move.company_id.account_fiscal_country_id.code == 'PT'
                and not move.l10n_pt_atcud
                and move.inalterable_hash
                and move.is_sale_document()
            ):
                at_series = self.env['l10n_pt.at.series'].search([('company_id', '=', move.company_id.id), ('prefix', '=', move.sequence_prefix[:-1])])
                move.l10n_pt_atcud = f"{at_series._get_at_code()}-{move.sequence_number}"
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
            amount_by_group = account_move.tax_totals['groups_by_subtotal']['Untaxed Amount']
            for group in amount_by_group:
                tax_group = self.env['account.tax.group'].browse(group['tax_group_id'])
                if (
                    tax_group.l10n_pt_tax_region == 'PT-ALL'  # I.e. tax is valid in all regions (PT, PT-AC, PT-MA)
                    or (
                        tax_group.l10n_pt_tax_region
                        and tax_group.l10n_pt_tax_region == account_move.company_id.l10n_pt_region_code
                    )
                ):
                    res[tax_group.l10n_pt_tax_category] = {
                        'base': format_amount(account_move, group['tax_group_base_amount']),
                        'vat': format_amount(account_move, group['tax_group_amount']),
                    }
            return res

        INVOICE_TYPE_MAP = {
            "out_invoice": "FT",
            "out_refund": "NC",
            "out_receipt": "FR",
        }

        for move in self.filtered(lambda m: (
            m.company_id.account_fiscal_country_id.code == "PT"
            and m.move_type in INVOICE_TYPE_MAP
            and m.inalterable_hash
            and not m.l10n_pt_qr_code_str  # Skip if already computed
        )):
            if not move.company_id.vat or not stdnum.pt.nif.is_valid(move.company_id.vat):
                action = self.env.ref('base.action_res_company_form')
                raise RedirectWarning(_('Please define the VAT on your company (e.g. PT123456789)'), action.id, _('Company Settings'))

            company_vat = re.sub(r'\D', '', move.company_id.vat)
            partner_vat = re.sub(r'\D', '', move.partner_id.vat or '999999990')
            details_by_tax_group = get_details_by_tax_category(move)
            tax_letter = 'I'
            if move.company_id.l10n_pt_region_code == 'PT-AC':
                tax_letter = 'J'
            elif move.company_id.l10n_pt_region_code == 'PT-MA':
                tax_letter = 'K'

            qr_code_str = ""
            qr_code_str += f"A:{company_vat}*"
            qr_code_str += f"B:{partner_vat}*"
            qr_code_str += f"C:{move.partner_id.country_id.code if move.partner_id and move.partner_id.country_id else 'Desconhecido'}*"
            qr_code_str += f"D:{INVOICE_TYPE_MAP[move.move_type]}*"
            qr_code_str += "E:N*"
            qr_code_str += f"F:{format_date(self.env, move.date, date_format='yyyyMMdd')}*"
            qr_code_str += f"G:{move._get_l10n_pt_document_number()}*"
            qr_code_str += f"H:{move.l10n_pt_atcud}*"
            qr_code_str += f"{tax_letter}1:{move.company_id.l10n_pt_region_code}*"
            if details_by_tax_group.get('E'):
                qr_code_str += f"{tax_letter}2:{details_by_tax_group.get('E')['base']}*"
            for i, tax_category in enumerate(('R', 'I', 'N')):
                if details_by_tax_group.get(tax_category):
                    qr_code_str += f"{tax_letter}{i * 2 + 3}:{details_by_tax_group.get(tax_category)['base']}*"
                    qr_code_str += f"{tax_letter}{i * 2 + 4}:{details_by_tax_group.get(tax_category)['vat']}*"
            qr_code_str += f"N:{format_amount(move, move.tax_totals['amount_total'] - move.tax_totals['amount_untaxed'])}*"
            qr_code_str += f"O:{format_amount(move, move.tax_totals['amount_total'])}*"
            qr_code_str += f"Q:{move.l10n_pt_inalterable_hash_short}*"
            qr_code_str += f"R:{PT_CERTIFICATION_NUMBER}"
            move.l10n_pt_qr_code_str = urllib.parse.quote_plus(qr_code_str)
