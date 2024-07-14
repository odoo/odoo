# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    project_id = fields.Many2one(domain="[('allow_timesheets', '=', True), ('company_id', '=', company_id), ('allow_billable', '=', use_helpdesk_sale_timesheet)]")

    def _create_project(self, name, allow_billable, other):
        new_values = dict(other, allow_billable=allow_billable)
        return super(HelpdeskTeam, self)._create_project(name, allow_billable, new_values)

    def write(self, vals):
        result = super(HelpdeskTeam, self).write(vals)
        if 'use_helpdesk_sale_timesheet' in vals and vals['use_helpdesk_sale_timesheet']:
            projects = self.filtered(lambda team: team.project_id).mapped('project_id')
            projects.write({'allow_billable': True, 'timesheet_product_id': projects._default_timesheet_product_id()})
        return result
