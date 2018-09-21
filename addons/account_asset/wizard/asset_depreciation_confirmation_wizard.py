# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AssetDepreciationConfirmationWizard(models.TransientModel):
    _name = "asset.depreciation.confirmation.wizard"
    _description = "Assets Depreciation Confirmation wizard"

    date = fields.Date('Account Date', required=True, help="Choose the period for which you want to automatically post the depreciation lines of running assets", default=fields.Date.context_today)

    @api.multi
    def asset_compute(self):
        self.ensure_one()
        context = self._context
        created_move_ids = self.env['account.asset.asset'].compute_generated_entries(self.date, asset_type=context.get('asset_type'))

        return {
            'name': _('Created Asset Moves') if context.get('asset_type') == 'purchase' else _('Created Revenue Moves'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',[" + ','.join(str(id) for id in created_move_ids) + "])]",
            'type': 'ir.actions.act_window',
        }
