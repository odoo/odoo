# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    worksheet_template_id = fields.Many2one(
        'worksheet.template', string="Worksheet Template",
        domain="[('res_model', '=', 'maintenance.request'), '|', ('company_ids', '=', False), ('company_ids', 'in', company_id)]",
        help="Create templates for each type of request you have and customize their content with your own custom fields.")
    worksheet_count = fields.Integer('Worksheet Count', compute='_compute_worksheet_count')

    @api.depends('worksheet_template_id')
    def _compute_worksheet_count(self):
        for record in self:
            count = 0
            if record.worksheet_template_id:
                x_model = self.env[record.worksheet_template_id.sudo().model_id.model]
                count = x_model.search_count([('x_maintenance_request_id', '=', record.id)])
            record.worksheet_count = count

    def action_maintenance_worksheet(self):
        self.ensure_one()
        if not self.worksheet_template_id:
            raise UserError(_("Please select a Worksheet Template."))
        action = self.worksheet_template_id.action_id.sudo().read()[0]
        x_model = self.env[self.worksheet_template_id.sudo().model_id.model]
        worksheet = x_model.search([('x_maintenance_request_id', '=', self.id)])
        context = literal_eval(action.get('context', '{}'))
        action.update({
            'res_id': worksheet.id if worksheet else False,
            'views': [(False, 'form')],
            'context': {
                **context,
                'edit': True,
                'default_x_maintenance_request_id': self.id,
            },
        })
        return action
