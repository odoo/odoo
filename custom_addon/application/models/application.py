from datetime import date
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Application(models.Model):
    _name = "application"

    def _get_years(self):
        year_list = []
        for i in range(date.today().year - 20, date.today().year + 20):
            year_list.append((str(i), str(i)))
        return year_list
    
    def _get_year_defaults(self):
        return str(date.today().year)
    
    year = fields.Selection(selection=_get_years, default=_get_year_defaults, string='Year', required=True, tracking=True)
    project_name = fields.Char('Project Name', tracking=True)
    main_focuses = fields.Char('Main focuses of the project', tracking=True)
    application_institution = fields.Char('Application institution/Unit', tracking=True)
    pi = fields.Char('PI', tracking=True)
    signature = fields.Char('Signature', tracking=True)
    date = fields.Date(string="Date", tracking=True, default=fields.Date.today)
    status = fields.Many2one('status.application', tracking=True, string="Status", default=lambda self: self.env['status.application'].search([('type_status', '=', 'to_submit')]).id)
    flag_status = fields.Char(string="Status Flag", readonly=True, store=True, compute='_compute_flag_status')
    atticles = fields.Text(string="Articles to be produced:")

    @api.depends('status')
    def _compute_flag_status(self):
        for record in self:
            record.flag_status= record.status.type_status

    def action_submit_application(self):
        self.status = self.env['status.application'].search([('type_status', '=', 'submitted')]).id

    def action_approve_application(self):
        self.status = self.env['status.application'].search([('type_status', '=', 'approved')]).id

class StatusApplication(models.Model):
    _name = "status.application"

    name = fields.Char('Status')
    type_status = fields.Char('Type')