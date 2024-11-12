# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    bom_count = fields.Integer(compute='_compute_bom_count', groups='mrp.group_mrp_user', export_string_translation=False)
    production_count = fields.Integer(compute='_compute_production_count', groups='mrp.group_mrp_user', export_string_translation=False)

    def _compute_bom_count(self):
        bom_count_per_project = dict(
            self.env['mrp.bom']._read_group(
                [('project_id', 'in', self.ids)],
                ['project_id'], ['__count']
            )
        )
        for project in self:
            project.bom_count = bom_count_per_project.get(project)

    def _compute_production_count(self):
        production_count_per_project = dict(
            self.env['mrp.production']._read_group(
                [('project_id', 'in', self.ids)],
                ['project_id'], ['__count']
            )
        )
        for project in self:
            project.production_count = production_count_per_project.get(project)

    def action_view_mrp_bom(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'domain': [('project_id', '=', self.id)],
            'name': self.env._('Bills of Materials'),
            'view_mode': 'list,form',
            'context': {'default_project_id': self.id},
            'help': "<p class='o_view_nocontent_smiling_face'>%s</p><p>%s</p>" % (
                _("No bill of materials found. Let's create one."),
                _("Bills of materials allow you to define the list of required raw materials used to make a finished "
                    "product; through a manufacturing order or a pack of products."),
            ),
        }
        boms = self.env['mrp.bom'].search([('project_id', '=', self.id)])
        if not self.env.context.get('from_embedded_action', False) and len(boms) == 1:
            action['views'] = [[False, 'form']]
            action['res_id'] = boms.id
        return action

    def action_view_mrp_production(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('mrp.mrp_production_action')
        action['domain'] = [('project_id', '=', self.id)]
        action['context'] = {'default_project_id': self.id, 'from_project_action': True}
        productions = self.env['mrp.production'].search([('project_id', '=', self.id)])
        if not self.env.context.get('from_embedded_action', False) and len(productions) == 1:
            action['views'] = [[False, 'form']]
            action['res_id'] = productions.id
        return action

    def _get_stat_buttons(self):
        buttons = super()._get_stat_buttons()
        if self.env.user.has_group('mrp.group_mrp_user'):
            self_sudo = self.sudo()
            buttons.extend([{
                'icon': 'flask',
                'text': self.env._('Bills of Materials'),
                'number': self_sudo.bom_count,
                'action_type': 'object',
                'action': 'action_view_mrp_bom',
                'show': self_sudo.bom_count > 0,
                'sequence': 35,
            },
            {
                'icon': 'wrench',
                'text': self.env._('Manufacturing Orders'),
                'number': self_sudo.production_count,
                'action_type': 'object',
                'action': 'action_view_mrp_production',
                'show': self_sudo.production_count > 0,
                'sequence': 46,
            }])
        return buttons
