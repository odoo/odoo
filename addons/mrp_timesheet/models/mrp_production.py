#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    timesheet_encode_uom_id = fields.Many2one('uom.uom', related='company_id.timesheet_encode_uom_id')
    timesheet_total_duration = fields.Integer(compute='_compute_timesheet_total_duration', groups="hr_timesheet.group_hr_timesheet_user")
    show_timesheets_button = fields.Boolean(compute='_compute_show_timesheets_button')

    def action_view_linked_project_timesheets(self):
        action = self.env['ir.actions.actions']._for_xml_id('hr_timesheet.act_hr_timesheet_line_by_project')
        action['domain'] = [('project_id', 'in', self.project_ids.ids)]
        action['context'] = {'default_project_id': self.project_ids[0].id, 'is_timesheet': 1}
        return action

    @api.depends('project_ids', 'project_ids.allow_timesheets')
    def _compute_show_timesheets_button(self):
        for production in self:
            production.show_timesheets_button = production.project_ids and any(production.project_ids.mapped('allow_timesheets'))

    @api.depends('project_ids')
    def _compute_timesheet_total_duration(self):
        for production in self:
            production.timesheet_total_duration = sum(production.project_ids.mapped('total_timesheet_time'))
