# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils
from odoo.addons.l10n_pt_pos.models.pos_order import PosOrder


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_pt_pos_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_pos.action_l10n_pt_pos_report_hash_integrity').report_action(self.id)

    def _l10n_pt_pos_check_hash_integrity(self):
        if self.country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))

        results = []

        self.env['pos.order'].l10n_pt_pos_compute_missing_hashes(self.id)
        public_key_string = L10nPtHashingUtils._l10n_pt_get_last_public_key(self.env)
        pos_configs = self.env['pos.config'].search([
            ('company_id', '=', self.id),
        ])

        for pos_config in pos_configs:
            pos_orders = self.env['pos.order'].sudo().search([
                ('config_id', '=', pos_config.id),
                ('l10n_pt_pos_inalterable_hash', '!=', False),
            ], order='name')
            results.append(
                L10nPtHashingUtils._l10n_pt_check_chain_hash_integrity(
                    pos_config.name, pos_orders, 'l10n_pt_pos_inalterable_hash',
                    'date_order', PosOrder._l10n_pt_pos_verify_integrity, public_key_string
                )
            )

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.to_string(fields.Date.context_today(self)))
        }
