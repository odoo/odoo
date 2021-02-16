# -*- coding: utf-8 -*-

from odoo import models, fields


class Faculty(models.Model):
    _name = 'rfp.faculty'
    _description = 'Faculty Data'

    name = fields.Char(string='Faculty Name', size=20, required=True)
    about = fields.Text(string='About', size=200, required=True)
    department_id = fields.Many2one('rfp.department', string='Department')
    department_about = fields.Text(related='department_id.about', string='Department About')