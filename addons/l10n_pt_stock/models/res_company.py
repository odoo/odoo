# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_pt_stock_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_stock.action_l10n_pt_stock_report_hash_integrity').report_action(self.id)

    def _l10n_pt_stock_check_hash_integrity(self):
        if self.country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))

        results = []

        self.env['stock.picking'].l10n_pt_stock_compute_missing_hashes(self.env.company.id)
        picking_types = self.env['stock.picking.type'].search([
            ('company_id', '=', self.env.company.id),
            ('code', '=', 'outgoing'),
            ('l10n_pt_stock_official_series_id', '!=', False),
        ])

        for picking_type in picking_types:
            pickings = self.env['stock.picking'].sudo().search([
                ('picking_type_id', '=', picking_type.id),
                ('l10n_pt_stock_inalterable_hash', '!=', False),
            ], order='l10n_pt_secure_sequence_number')
            if not pickings:
                results.append({
                    'name': picking_type.name,
                    'status': 'no_data',
                    'msg': _('There is no entry flagged for data inalterability yet.'),
                })
                continue

            public_key_string = L10nPtHashingUtils._l10n_pt_get_last_public_key(self.env)

            hash_corrupted = False
            previous_hash = ""
            for picking in pickings:
                if not picking._l10n_pt_stock_verify_integrity(previous_hash, public_key_string):
                    results.append({
                        'name': picking_type.name,
                        'status': 'corrupted',
                        'msg': _("Corrupted data on record with id %s.", picking.id),
                    })
                    hash_corrupted = True
                    break
                previous_hash = picking.l10n_pt_stock_inalterable_hash

            if not hash_corrupted:
                results.append({
                    'name': picking_type.name,
                    'status': 'verified',
                    'msg': _("Entries are correctly hashed"),
                    'from_name': pickings[0].name,
                    'from_hash': pickings[0].l10n_pt_stock_inalterable_hash,
                    'from_date': fields.Date.to_string(pickings[0].date),
                    'to_name': pickings[-1].name,
                    'to_hash':  pickings[-1].l10n_pt_stock_inalterable_hash,
                    'to_date': fields.Date.to_string(pickings[-1].date),
                })

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.to_string(fields.Date.context_today(self)))
        }
