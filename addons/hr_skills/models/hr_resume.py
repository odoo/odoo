# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class Employee(models.Model):
    _inherit = 'hr.employee'

    resume_line_ids = fields.One2many('hr.resume.line', 'employee_id', string="Resumé lines", ondelete='cascade')


    @api.model
    def create(self, vals):
        res = super(Employee, self).create(vals)
        self.env['hr.resume.line'].create({
            'employee_id': res.id,
            'name': res.company_id.name,
            'date_start': res.create_date.date(),
            'description': "",
            'line_type_id': self.env.ref('hr_skills.resume_type_experience').id
        })
        return res


class ResumeLine(models.Model):
    _name = 'hr.resume.line'
    _description = "Resumé line of an employee"

    employee_id = fields.Many2one('hr.employee', required=True)
    name = fields.Char(required=True)
    date_start = fields.Date(required=True)
    date_end = fields.Date()
    description = fields.Html(string="Description")
    line_type_id = fields.Many2one('hr.resume.line.type', string="Type")
    sequence = fields.Integer(default=100)

    _sql_constraints = [
        ('date_check', "CHECK ((date_start <= date_end OR date_end = NULL))", "The start date must be anterior to the end date."),
    ]

class ResumeLineType(models.Model):
    _name = 'hr.resume.line.type'
    _description = "Type of a resumé line"

    name = fields.Char(required=True)