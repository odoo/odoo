# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _lt, _


class Project(models.Model):
    _inherit = "project.project"

    production_ids = fields.Many2many('mrp.production', groups='mrp.group_mrp_user')
    bom_ids = fields.Many2many('mrp.bom', groups='mrp.group_mrp_user')
    production_count = fields.Integer(compute='_compute_production_count')
    bom_count = fields.Integer(compute='_compute_bom_count')

    @api.depends('production_ids')
    def _compute_production_count(self):
        for record in self:
            record.production_count = len(record.production_ids)

    @api.depends('bom_ids')
    def _compute_bom_count(self):
        for record in self:
            record.bom_count = len(record.bom_ids)

    def action_view_mrp_production(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('mrp.mrp_production_action')
        action['domain'] = [['id', 'in', self.production_ids.ids]]
        action['context'] = {'default_project_ids': [self.id]}
        if self.production_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.production_ids.id
            if 'views' in action:
                action['views'] = [
                    (view_id, view_type)
                    for view_id, view_type in action['views']
                    if view_type == 'form'
                ] or [False, 'form']
        return action

    def action_view_mrp_bom(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "res_model": "mrp.bom",
            "domain": [['id', 'in', self.bom_ids.ids]],
            "name": _("Bills of Materials"),
            'view_mode': 'tree,form,kanban',
            "context": {'default_project_ids': [self.id]},
        }
        if self.bom_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.bom_ids.id
        return action

    def _get_stat_buttons(self):
        buttons = super()._get_stat_buttons()
        if self.env.user.has_group('mrp.group_mrp_user'):
            self_sudo = self.sudo()
            buttons.extend([
                {
                    'icon': 'flask',
                    'text': _lt('Bills of Materials'),
                    'number': self_sudo.bom_count,
                    'action_type': 'object',
                    'action': 'action_view_mrp_bom',
                    'show': self_sudo.bom_count > 0,
                    'sequence': 35,
                },
                {
                    'icon': 'wrench',
                    'text': _lt('Manufacturing Orders'),
                    'number': self_sudo.production_count,
                    'action_type': 'object',
                    'action': 'action_view_mrp_production',
                    'show': self_sudo.production_count > 0,
                    'sequence': 46,
                }
            ])
        return buttons
