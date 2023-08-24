# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.tools.misc import format_date
from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils
from odoo.addons.l10n_pt_account.models.account_move import AccountMove


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_account_region_code = fields.Char(compute='_compute_l10n_pt_region_code', store=True, readonly=False)

    @api.depends('country_id', 'state_id')
    def _compute_l10n_pt_region_code(self):
        for company in self.filtered(lambda c: c.country_id.code == 'PT'):
            if company.state_id == self.env.ref('base.state_pt_pt-20'):
                company.l10n_pt_account_region_code = 'PT-AC'
            elif company.state_id == self.env.ref('base.state_pt_pt-30'):
                company.l10n_pt_account_region_code = 'PT-MA'
            else:
                company.l10n_pt_account_region_code = 'PT'

    def _check_accounting_hash_integrity(self):
        """Checks that all posted moves have still the same data as when they were posted
        and raises an error with the result.
        """
        if self.account_fiscal_country_id.code != 'PT':
            return super()._check_accounting_hash_integrity()

        journals = self.env['account.journal'].search([('company_id', '=', self.id), ('restrict_mode_hash_table', '=', True)])
        results = []

        self.env['account.move'].l10n_pt_account_compute_missing_hashes(self.env.company.id)

        for journal in journals:
            all_moves = self.env['account.move'].sudo().search([
                ('journal_id', '=', journal.id),
                ('inalterable_hash', '!=', False),
            ])
            if not all_moves:
                results.append({
                    'name': f"{journal.name} [{journal.code}]",
                    'status': 'no_data',
                    'msg': _('There is no journal entry flagged for data inalterability yet.'),
                })
                continue

            public_key_string = L10nPtHashingUtils._l10n_pt_get_last_public_key(self.env)

            # We have one chain per (move_type, sequence_prefix) pair.
            chains = all_moves.grouped(lambda m: (m.move_type, m.sequence_prefix))

            for chain_prefix in chains.keys():
                chain = chains[chain_prefix].sorted('sequence_number')
                results.append(
                    L10nPtHashingUtils._l10n_pt_check_chain_hash_integrity(
                        f"{journal.name} [{chain_prefix[1]}]", chain, 'inalterable_hash',
                        'date', AccountMove._l10n_pt_account_verify_integrity, public_key_string
                    )
                )

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.to_string(fields.Date.context_today(self)))
        }
