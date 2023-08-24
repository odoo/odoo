# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.addons.l10n_pt_account.utils.hashing import L10nPtHashingUtils
from odoo.addons.l10n_pt_stock.models.stock_picking import StockPicking


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_pt_stock_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_stock.action_l10n_pt_stock_report_hash_integrity').report_action(self.id)

    def _l10n_pt_stock_check_hash_integrity(self):
        if self.country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))

        results = []

        picking_types = self.env['stock.picking.type'].search([
            ('company_id', '=', self.id),
            ('code', '=', 'outgoing'),
            ('l10n_pt_stock_official_series_id', '!=', False),
        ])
        public_key_string = L10nPtHashingUtils._l10n_pt_get_last_public_key(self.env)

        for picking_type in picking_types:
            pickings = self.env['stock.picking'].sudo().search([
                ('picking_type_id', '=', picking_type.id),
                ('l10n_pt_stock_inalterable_hash', '!=', False),
            ], order='l10n_pt_stock_secure_sequence_number')
            results.append(
                L10nPtHashingUtils._l10n_pt_check_chain_hash_integrity(
                    picking_type.name, pickings, 'l10n_pt_stock_inalterable_hash',
                    'date_done', StockPicking._l10n_pt_stock_verify_integrity, public_key_string
                )
            )

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.to_string(fields.Date.context_today(self)))
        }
