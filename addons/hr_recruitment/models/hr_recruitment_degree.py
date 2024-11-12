# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrRecruitmentDegree(models.Model):
    _name = 'hr.recruitment.degree'
    _description = "Applicant Degree"

    name = fields.Char("Degree Name", required=True, translate=True)
    sequence = fields.Integer("Sequence", default=1)

    _name_uniq = models.Constraint(
        'unique (name)',
        'The name of the Degree of Recruitment must be unique!',
    )
