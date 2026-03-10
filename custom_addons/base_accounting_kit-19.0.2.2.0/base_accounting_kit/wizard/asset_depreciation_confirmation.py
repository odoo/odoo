# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models, _


class AssetDepreciationConfirmationWizard(models.TransientModel):
    _name = "asset.depreciation.confirmation"
    _description = "Asset Depreciation Confirmation"

    date = fields.Date('Account Date', required=True,
                       help="Choose the period for which you want to automatically "
                            "post the depreciation lines of running assets",
                       default=fields.Date.context_today)

    def asset_compute(self):
        self.ensure_one()
        context = self._context
        created_move_ids = self.env['account.asset.asset'].sudo().compute_generated_entries(self.date, asset_type=context.get('asset_type'))
        moves = self.env['account.move'].browse(created_move_ids)
        auto_post_draft_moves = moves.filtered(lambda move: move.state == 'draft' and move.auto_post)
        auto_post_draft_moves.write({'auto_post': 'at_date'})
        return {
            'name': _('Created Asset Moves') if context.get('asset_type') == 'purchase' else _('Created Revenue Moves'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',[" + ','.join(str(id) for id in created_move_ids) + "])]",
            'type': 'ir.actions.act_window',
        }


