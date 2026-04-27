# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    l10n_be_scale_category = fields.Selection([
        ('A', 'Category A'),
        ('B', 'Category B'),
        ('C', 'Category C'),
        ('D', 'Category D'),
    ], default='C', help="""Category A - Executive functions:
Included in this class are functions characterized by performing a limited number of simple and repetitive tasks. For example: the worker exclusively responsible for typing.

Category B - Support functions.
Included in this class are functions characterized by making a contribution to the achievement of a larger mission. For example: the administrative employee or the receptionist.

Category C - Management functions.
Included in this class are functions characterized by carrying out a complete set of tasks which, together, constitute one and the same mission. For example: the personnel administration employee or the PC technician.

Category D - Advisory functions.
Included in this class are functions characterized by monitoring and developing the same professional process within the framework of a specific objective. For example: the programmer, accountant or consultant""")
    display_l10n_be_scale = fields.Boolean(compute='_compute_display_be')

    @api.depends('company_id')
    def _compute_display_be(self):
        for job in self:
            job.display_l10n_be_scale = job.company_id.country_id.code == 'BE'
