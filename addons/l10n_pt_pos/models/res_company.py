# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_pt_pos_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_pos.action_l10n_pt_pos_report_hash_integrity').report_action(self.id)

    def _l10n_pt_pos_check_hash_integrity(self):
        if self.country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))

        results = []

        self.env['pos.order'].l10n_pt_pos_compute_missing_hashes(self.env.company.id)
        pos_configs = self.env['pos.config'].search([
            ('company_id', '=', self.env.company.id),
        ])

        for pos_config in pos_configs:
            pos_orders = self.env['pos.order'].sudo().search([
                ('config_id', '=', pos_config.id),
                ('l10n_pt_pos_inalterable_hash', '!=', False),
            ], order='name')
            if not pos_orders:
                results.append({
                    'name': pos_config.name,
                    'status': 'no_data',
                    'msg': _('There is no entry flagged for data inalterability yet.'),
                })
                continue

            public_key_string = L10nPtHashingUtils._l10n_pt_get_last_public_key(self.env)

            hash_corrupted = False
            previous_hash = ""
            for order in pos_orders:
                if not order._l10n_pt_pos_verify_integrity(previous_hash, public_key_string):
                    results.append({
                        'name': pos_config.name,
                        'status': 'corrupted',
                        'msg': _("Corrupted data on record with id %s.", order.id),
                    })
                    hash_corrupted = True
                    break
                previous_hash = order.l10n_pt_pos_inalterable_hash

            if not hash_corrupted:
                results.append({
                    'name': pos_config.name,
                    'status': 'verified',
                    'msg': _("Entries are correctly hashed"),
                    'from_name': pos_orders[0].name,
                    'from_hash': pos_orders[0].l10n_pt_pos_inalterable_hash,
                    'from_date': fields.Date.to_string(pos_orders[0].date_order),
                    'to_name': pos_orders[-1].name,
                    'to_hash':  pos_orders[-1].l10n_pt_pos_inalterable_hash,
                    'to_date': fields.Date.to_string(pos_orders[-1].date_order),
                })

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.to_string(fields.Date.context_today(self)))
        }
