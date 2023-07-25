import re
import urllib.parse
import stdnum.pt.nif

from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_repr, groupby, format_date


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_pt_account_qr_code_str = fields.Char(string='Portuguese QR Code', compute='_compute_l10n_pt_account_qr_code_str', store=True)
    l10n_pt_account_inalterable_hash_short = fields.Char(string='Short version of the Portuguese hash', compute='_compute_l10n_pt_account_inalterable_hash')
    l10n_pt_account_inalterable_hash_version = fields.Integer(string='Portuguese hash version', compute='_compute_l10n_pt_account_inalterable_hash')
    l10n_pt_account_atcud = fields.Char(string='Portuguese ATCUD', compute='_compute_l10n_pt_account_atcud', store=True)
    l10n_pt_account_show_future_date_warning = fields.Boolean(compute='_compute_l10n_pt_show_future_date_warning')

    @api.depends('inalterable_hash')
    def _compute_l10n_pt_account_inalterable_hash(self):
        for move in self:
            if move.inalterable_hash:
                hash_version, hash_str = move.inalterable_hash.split("$")[1:]
                move.l10n_pt_account_inalterable_hash_version = int(hash_version)
                move.l10n_pt_account_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                move.l10n_pt_account_inalterable_hash_short = False

    @api.depends(
        'sequence_number',
        'inalterable_hash',
        'journal_id.l10n_pt_account_invoice_official_series_id.code',
        'journal_id.l10n_pt_account_refund_official_series_id.code',
    )
    def _compute_l10n_pt_account_atcud(self):
        for move in self:
            if (
                move.company_id.account_fiscal_country_id.code == 'PT'
                and not move.l10n_pt_account_atcud
                and move.journal_id.l10n_pt_account_invoice_official_series_id
                and move.journal_id.l10n_pt_account_refund_official_series_id
                and move.inalterable_hash
                and move.is_sale_document()
            ):
                official_series = move.journal_id.l10n_pt_account_invoice_official_series_id if move.move_type == 'out_invoice' else move.journal_id.l10n_pt_account_refund_official_series_id
                move.l10n_pt_account_atcud = f"{official_series.code}-{move.sequence_number}"
            else:
                move.l10n_pt_account_atcud = False

    @api.depends('state', 'invoice_date', 'company_id.account_fiscal_country_id.code')
    def _compute_l10n_pt_show_future_date_warning(self):
        for move in self:
            move.l10n_pt_account_show_future_date_warning = (
                move.company_id.account_fiscal_country_id.code == 'PT'
                and move.state == 'draft'
                and move.invoice_date
                and move.invoice_date > fields.Date.today()
            )

    @api.depends('l10n_pt_account_atcud')
    def _compute_l10n_pt_account_qr_code_str(self):
        """ Generate the informational QR code for Portugal invoicing.
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
            """Returns the base and value tax for each PT tax category (Normal, Intermediate, Reduced, Exempt)"""
            res = {}
            amount_by_group = account_move.tax_totals['groups_by_subtotal']['Untaxed Amount']
            for group in amount_by_group:
                tax_group = self.env['account.tax.group'].browse(group['tax_group_id'])
                if (
                        not tax_group.l10n_pt_account_tax_region  # I.e. tax is valid in all regions (PT, PT-AC, PT-MA)
                        or (
                        tax_group.l10n_pt_account_tax_region
                        and tax_group.l10n_pt_account_tax_region == account_move.company_id.l10n_pt_account_region_code
                )
                ):
                    res[tax_group.l10n_pt_account_tax_category] = {
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
                and not m.l10n_pt_account_qr_code_str  # Skip if already computed
        )):
            if not move.inalterable_hash:
                continue
            company_vat_ok = move.company_id.vat and stdnum.pt.nif.is_valid(move.company_id.vat)
            atcud_ok = move.l10n_pt_account_atcud

            if not company_vat_ok or not atcud_ok:
                error_msg = _("Some fields required for the generation of the document are missing or invalid. Please verify them:\n")
                error_msg += _('- The `VAT` of your company should be defined and match the following format: PT123456789\n') if not company_vat_ok else ""
                error_msg += _("- The `ATCUD` is not defined. Please verify the journal's official series") if not atcud_ok else ""
                raise UserError(error_msg)

            company_vat = re.sub(r'\D', '', move.company_id.vat)
            partner_vat = re.sub(r'\D', '', move.partner_id.vat or '999999990')
            details_by_tax_group = get_details_by_tax_category(move)
            tax_letter = 'I'
            if move.company_id.l10n_pt_account_region_code == 'PT-AC':
                tax_letter = 'J'
            elif move.company_id.l10n_pt_account_region_code == 'PT-MA':
                tax_letter = 'K'

            qr_code_str = ""
            qr_code_str += f"A:{company_vat}*"
            qr_code_str += f"B:{partner_vat}*"
            qr_code_str += f"C:{move.partner_id.country_id.code if move.partner_id and move.partner_id.country_id else 'Desconhecido'}*"
            qr_code_str += f"D:{INVOICE_TYPE_MAP[move.move_type]}*"
            qr_code_str += "E:N*"
            qr_code_str += f"F:{format_date(self.env, move.date, date_format='yyyyMMdd')}*"
            qr_code_str += f"G:{move._get_l10n_pt_account_document_number()}*"
            qr_code_str += f"H:{move.l10n_pt_account_atcud}*"
            qr_code_str += f"{tax_letter}1:{move.company_id.l10n_pt_account_region_code}*"
            if details_by_tax_group.get('E'):
                qr_code_str += f"{tax_letter}2:{details_by_tax_group.get('E')['base']}*"
            for i, tax_category in enumerate(('R', 'I', 'N')):
                if details_by_tax_group.get(tax_category):
                    qr_code_str += f"{tax_letter}{i * 2 + 3}:{details_by_tax_group.get(tax_category)['base']}*"
                    qr_code_str += f"{tax_letter}{i * 2 + 4}:{details_by_tax_group.get(tax_category)['vat']}*"
            qr_code_str += f"N:{format_amount(move, move.tax_totals['amount_total'] - move.tax_totals['amount_untaxed'])}*"
            qr_code_str += f"O:{format_amount(move, move.tax_totals['amount_total'])}*"
            qr_code_str += f"Q:{move.l10n_pt_account_inalterable_hash_short}*"
            qr_code_str += "R:0000"  # TODO: Fill with Certificate number provided by the Tax Authority
            move.l10n_pt_account_qr_code_str = urllib.parse.quote_plus(qr_code_str)

    def _l10n_pt_get_vat_exemptions_reasons(self):
        self.ensure_one()
        return sorted(set(
            self.invoice_line_ids.tax_ids
                .filtered(lambda tax: tax.l10n_pt_account_tax_exemption_reason)
                .mapped(lambda tax: dict(tax._fields['l10n_pt_account_tax_exemption_reason'].selection).get(tax.l10n_pt_account_tax_exemption_reason))
        ))

    def _l10n_pt_check_invoice_date(self):
        """
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series" - Portuguese Tax Authority
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

    def action_reverse(self):
        for move in self.filtered(lambda m: m.company_id.account_fiscal_country_id.code == "PT"):
            if move.payment_state == 'reversed':
                raise UserError(_("You cannot reverse an invoice that has already been fully reversed."))
        return super().action_reverse()

    def action_post(self):
        for move in self.filtered(lambda m: m.company_id.account_fiscal_country_id.code == 'PT').sorted('invoice_date'):
            move._l10n_pt_check_invoice_date()
        return super().action_post()

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------
    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_integrity_hash_fields()
        return ['invoice_date', 'create_date', 'amount_total', 'l10n_pt_document_number', 'move_type', 'sequence_prefix', 'sequence_number']

    def _get_l10n_pt_account_document_number(self):
        self.ensure_one()
        return f"{self.move_type} {re.sub(r'[^A-Za-z0-9]+', '_', self.sequence_prefix).rstrip('_') }/{self.sequence_number}"

    def _hash_compute(self, previous_hash=None):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._hash_compute(previous_hash=previous_hash)
        if not self._context.get('l10n_pt_force_compute_signature'):
            return {}
        endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_pt_account.iap_endpoint', L10nPtHashingUtils.L10N_PT_SIGN_DEFAULT_ENDPOINT)
        if endpoint == 'demo':
            return self._l10n_pt_account_sign_records_using_demo_key(previous_hash)  # sign locally with the demo key provided by the government
        return self._l10n_pt_account_sign_records_using_iap(previous_hash)  # sign the records using Odoo's IAP (or a custom endpoint)

    def _l10n_pt_account_sign_records_using_iap(self, previous_hash):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        docs_to_sign = [{
            'id': move.id,
            'sorting_key': move.sequence_number,
            'date': move.date.isoformat(),
            'system_entry_date': move.create_date.isoformat(timespec='seconds'),
            'l10n_pt_document_number': move._get_l10n_pt_account_document_number(),
            'gross_total': float_repr(move.amount_total, 2),
            'previous_signature': previous_hash
        } for move in self]
        return L10nPtHashingUtils._l10n_pt_sign_records_using_iap(self.env, docs_to_sign)

    def _l10n_pt_account_get_message_to_hash(self, previous_hash):
        self.ensure_one()
        return L10nPtHashingUtils._l10n_pt_get_message_to_hash(self.date, self.create_date, self.amount_total, self._get_l10n_pt_account_document_number(), previous_hash)

    def _l10n_pt_account_get_last_record(self):
        self.ensure_one()
        return self.sudo().search([
            ('journal_id', '=', self.journal_id.id),
            ('state', '=', 'posted'),
            ('sequence_prefix', '=', self.sequence_prefix),
            ('sequence_number', '=', self.sequence_number - 1),
            ('inalterable_hash', '!=', False),
        ], limit=1)

    def _l10n_pt_account_sign_records_using_demo_key(self, previous_hash):
        """
        Technical requirements from the Portuguese tax authority can be found at page 13 of the following document:
        https://info.portaldasfinancas.gov.pt/pt/docs/Portug_tax_system/Documents/Order_No_8632_2014_of_the_3rd_July.pdf
        """
        res = {}
        for move in self:
            if not previous_hash:
                previous = move._l10n_pt_account_get_last_record()
                previous_hash = previous.inalterable_hash if previous else ""
            previous_hash = previous_hash.split("$")[2] if previous_hash else ""
            message = move._l10n_pt_account_get_message_to_hash(previous_hash)
            res[move.id] = L10nPtHashingUtils._l10n_pt_sign_using_demo_key(self.env, message)
            previous_hash = res[move.id]
        return res

    def _l10n_pt_account_verify_integrity(self, previous_hash, public_key_string):
        """
        :return: True if the hash of the record is valid, False otherwise
        """
        self.ensure_one()
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        message = self._l10n_pt_account_get_message_to_hash(previous_hash)
        return L10nPtHashingUtils._l10n_pt_verify_integrity(message, self.inalterable_hash, public_key_string)

    @api.model
    def l10n_pt_account_compute_missing_hashes(self, company_id):
        """
        Compute the hash for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        if self.env['res.company'].browse(company_id).account_fiscal_country_id.code != 'PT':
            return
        all_moves = self.search([
            ('company_id', '=', company_id),
            ('restrict_mode_hash_table', '=', True),
            ('state', '=', 'posted'),
            ('inalterable_hash', '=', False),
        ], order='sequence_prefix,sequence_number')
        grouped = groupby(all_moves.filtered(lambda m: m.restrict_mode_hash_table and not m.inalterable_hash), key=lambda m: m.sequence_prefix)
        for prefix, moves in grouped:
            moves = sorted(moves, key=lambda m: m.sequence_number)
            moves_hashes = self.env['account.move'].browse([m.id for m in moves]).with_context(l10n_pt_force_compute_signature=True)._hash_compute()
            for move_id, inalterable_hash in moves_hashes.items():
                super(AccountMove, self.env['account.move'].browse(move_id)).write({'inalterable_hash': inalterable_hash})

    def preview_invoice(self):
        self.l10n_pt_account_compute_missing_hashes(self.company_id.id)
        return super().preview_invoice()

    def action_send_and_print(self):
        self.l10n_pt_account_compute_missing_hashes(self.company_id.id)
        return super().action_send_and_print()

    def action_invoice_sent(self):
        self.l10n_pt_account_compute_missing_hashes(self.company_id.id)
        return super().action_invoice_sent()
