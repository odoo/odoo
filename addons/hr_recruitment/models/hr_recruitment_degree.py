# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrRecruitmentDegree(models.Model):
    _name = 'hr.recruitment.degree'
    _description = "Applicant Degree"

    name = fields.Char("Degree Name", required=True, translate=True)
    score = fields.Float("Score", required=True, default=0)
    sequence = fields.Integer("Sequence", default=1)

    _name_uniq = models.Constraint(
        'unique (name)',
        'The name of the Degree of Recruitment must be unique!',
    )
    _score_range = models.Constraint(
        'check(score >= 0 and score <= 1)',
        'Score should be between 0 and 100%',
    )
