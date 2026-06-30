# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    project_id = fields.Many2one('project.project', compute='_compute_project_id', domain=[('is_template', '=', False)], readonly=False, store=True)

    @api.depends('bom_id')
    def _compute_project_id(self):
        if not self.env.context.get('from_project_action'):
            for production in self:
                production.project_id = production.bom_id.project_id

    def action_generate_bom(self):
        action = super().action_generate_bom()
        action['context']['default_project_id'] = self.project_id.id
        return action

    def action_open_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'form',
            'res_id': self.project_id.id,
        }
