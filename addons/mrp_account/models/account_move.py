# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    wip_production_ids = fields.Many2many(
        'mrp.production', 'wip_move_production_rel', 'move_id', 'production_id', string="Relevant WIP MOs",
        copy=False,
        help="The MOs that this WIP entry was based on. Expected to be set at time of WIP entry creation.")
    wip_production_count = fields.Integer("Manufacturing Orders Count", compute='_compute_wip_production_count')

    def copy(self, default=None):
        records = super().copy(default)
        for record, source in zip(records.sudo(), self.sudo()):
            record.wip_production_ids = source.wip_production_ids
        return records

    @api.depends('wip_production_ids')
    def _compute_wip_production_count(self):
        for account in self:
            account.wip_production_count = len(account.wip_production_ids)

    def action_view_wip_production(self):
        self.ensure_one()
        action = {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
        }
        if len(self.wip_production_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.wip_production_ids.id,
            })
        else:
            action.update({
                'name': _("WIP MOs of %s", self.name),
                'domain': [('id', 'in', self.wip_production_ids.ids)],
                'view_mode': 'list,form',
            })
        return action


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
