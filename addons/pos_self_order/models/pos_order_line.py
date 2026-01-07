# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    combo_id = fields.Many2one('product.combo', string='Combo Reference')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._handle_combo_parent_uuid(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._handle_combo_parent_uuid(vals)
        return super().write(vals)

    def _handle_combo_parent_uuid(self, vals):
        if combo_parent_uuid := vals.get('combo_parent_uuid'):
            vals['combo_parent_id'] = self.search([
                ('uuid', '=', combo_parent_uuid)
            ], limit=1).id
        if 'combo_parent_uuid' in vals:
            del vals['combo_parent_uuid']
