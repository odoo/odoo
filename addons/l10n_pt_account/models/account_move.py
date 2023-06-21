# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'l10n_pt.mixin']

    l10n_pt_date = fields.Date(string="Date of the document used for the signature", related='invoice_date')
    l10n_pt_gross_total = fields.Monetary(string="Gross total of the document used for the signature", related='amount_total')

    # Override l10n_pt.mixin
    @api.depends('company_id.account_fiscal_country_id.code', 'move_type', 'sequence_prefix', 'sequence_number')
    def _compute_l10n_pt_document_number(self):
        for move in self.filtered(lambda m: (
            m.company_id.account_fiscal_country_id.code == 'PT'
            and m.state == 'posted'
            and m.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
            and m.sequence_prefix
            and m.sequence_number
            and m.invoice_date
            and not m.l10n_pt_document_number
        )):
            seq_info = self._l10n_pt_get_sanitized_sequence_info(move.sequence_prefix, number=move.sequence_number)
            move.l10n_pt_document_number = f"{move.move_type} {seq_info}"

    def _compute_blockchain_must_hash(self):
        for move in self.filtered(lambda m: m.company_id.account_fiscal_country_id.code == 'PT'):
            move.blockchain_must_hash = move.blockchain_must_hash or move.blockchain_secure_sequence_number or (
                move.restrict_mode_hash_table
                and move.l10n_pt_document_number
            )
        super(AccountMove, self.filtered(lambda m: m.company_id.account_fiscal_country_id.code != 'PT'))._compute_blockchain_must_hash()

    def _get_blockchain_previous_record_domain(self):
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_blockchain_previous_record_domain()

        # Different from account.move because in Portugal the previous record is not the
        # latest posted account.move but the latest posted account.move with the same move_type
        # so the blockchain_secure_sequence_number is not necessarily the highest one
        return [
            ('state', '=', 'posted'),
            ('move_type', '=', self.move_type),
            ('journal_id', '=', self.journal_id.id),
            ('blockchain_secure_sequence_number', '<', self.blockchain_secure_sequence_number),
            ('blockchain_secure_sequence_number', '!=', 0)
        ]

    def _compute_blockchain_inalterable_hash(self):
        """
        We need an optimization for Portugal where the hash is only computed
        when we actually need it (printing of an invoice or the integrity report).
        This is because in Portugal's case, the hash is computed by Odoo's IAP
        service which needs an RPC call that might be slow.
        """
        super(AccountMove, self.filtered(lambda m: m.company_id.account_fiscal_country_id.code != 'PT'))._compute_blockchain_inalterable_hash()
        if self._context.get('l10n_pt_force_compute_signature'):
            super(AccountMove, self.filtered(lambda m: m.company_id.account_fiscal_country_id.code == 'PT'))._l10n_pt_compute_blockchain_inalterable_hash()

    def _get_blockchain_inalterable_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_blockchain_inalterable_hash_fields()
        return ['invoice_date', 'create_date', 'amount_total', 'l10n_pt_document_number', 'move_type', 'sequence_prefix', 'sequence_number']

    def _get_blockchain_record_hash_string(self, previous_hash=None):
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_blockchain_record_hash_string(previous_hash)
        return self._l10n_pt_get_blockchain_record_hash_string(previous_hash)

    def preview_invoice(self):
        self.l10n_pt_compute_missing_hashes(self.company_id.id)
        return super().preview_invoice()

    def action_send_and_print(self):
        self.l10n_pt_compute_missing_hashes(self.company_id.id)
        return super().action_send_and_print()

    def action_invoice_sent(self):
        self.l10n_pt_compute_missing_hashes(self.company_id.id)
        return super().action_invoice_sent()

    @api.model
    def _l10n_pt_account_cron_compute_missing_hashes(self):
        companies = self.env['res.company'].search([('account_fiscal_country_id', '=', self.env.ref('base.pt').id)])
        for company in companies:
            self.env['account.move'].l10n_pt_compute_missing_hashes(company.id)
