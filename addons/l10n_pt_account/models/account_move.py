import re

from addons.l10n_pt.utils.hashing import L10nPtHashingUtils
from odoo import models
from odoo.tools import float_repr, groupby


class AccountMove(models.Model):
    _inherit = "account.move"

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
        endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', L10nPtHashingUtils.L10N_PT_SIGN_DEFAULT_ENDPOINT)
        if endpoint == 'demo':
            return self._l10n_pt_account_sign_records_using_demo_key(previous_hash)  # sign locally with the demo key provided by the government
        return self._l10n_pt_account_sign_records_using_iap(previous_hash)  # sign the records using Odoo's IAP (or a custom endpoint)

    def _l10n_pt_account_sign_records_using_iap(self, previous_hash):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        docs_to_sign = [{
            'id': move.id,
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

    def _l10n_pt_account_verify_integrity(self, previous_hash):
        """
        :return: True if the hash of the record is valid, False otherwise
        """
        self.ensure_one()
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        message = self._l10n_pt_account_get_message_to_hash(previous_hash)
        return L10nPtHashingUtils._l10n_pt_verify_integrity(self.env, message, self.inalterable_hash)

    def l10n_pt_account_compute_missing_hashes(self, company_id):
        """
        Compute the hash for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
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
