# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class GradeMessageConfiguration(models.Model):
    _name = 'grade.message.configuration'
    _description = 'Grade Message Configuration'
    _rec_name = 'description'

    product_grade = fields.Selection([
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C')
    ], string='Product Grade', tracking=True)

    description = fields.Char(
        string='Grade Message Description',
        required=True,
        help='Short description or message text',
        tracking=True
    )

