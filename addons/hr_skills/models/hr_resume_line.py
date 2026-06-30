# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models


class HrResumeLine(models.Model):
    _name = 'hr.resume.line'
    _description = "Resume line of an employee"
    _order = "line_type_id, date_end desc, date_start desc"

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, ondelete='cascade', index=True)
    avatar_128 = fields.Image(related='employee_id.avatar_128')
    company_id = fields.Many2one(related='employee_id.company_id')
    department_id = fields.Many2one(related='employee_id.department_id')
    name = fields.Char(required=True, translate=True)
    date_start = fields.Date(required=True, default=fields.Date.context_today)
    date_end = fields.Date()
    duration = fields.Integer(string="Duration")
    description = fields.Html(string="Description", translate=True)
    line_type_id = fields.Many2one('hr.resume.line.type', string="Type")
    is_course = fields.Boolean(related='line_type_id.is_course')
    course_type = fields.Selection(
        string="Course Type",
        selection=[('external', 'External')],
        default='external',
        required=True
    )
    color = fields.Char(compute='_compute_color', default='#000000')
    external_url = fields.Char(string="External URL", compute='_compute_external_url', store=True, readonly=False)
    certificate_filename = fields.Char()
    certificate_file = fields.Binary(string="Certificate")
    resume_line_properties = fields.Properties(
        'Properties',
        definition='line_type_id.resume_line_type_properties_definition'
    )

    _date_check = models.Constraint(
        'CHECK ((date_start <= date_end OR date_end IS NULL))',
        'The start date must be anterior to the end date.',
    )

    @api.onchange('external_url')
    def _onchange_external_url(self):
        if not self.name and self.external_url:
            website_name_match = re.search(r'((https|http):\/\/)?(www\.)?(.*)\.', self.external_url)
            if website_name_match:
                self.name = website_name_match.group(4).capitalize()

    @api.depends('course_type')
    def _compute_external_url(self):
        for resume_line in self:
            if resume_line.course_type != 'external':
                resume_line.external_url = ''

    @api.depends('course_type')
    def _compute_color(self):
        for resume_line in self:
            if resume_line.course_type == 'external':
                resume_line.color = '#a2a2a2'
