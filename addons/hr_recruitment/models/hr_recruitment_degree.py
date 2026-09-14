from odoo import fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class HrRecruitmentDegree(models.Model):
    _name = "hr.recruitment.degree"
    _description = "Applicant Degree"
    _order = "sequence"

    name = fields.Char(
        string="Degree Name",
        translate=True,
        required=True,
    )
    score = fields.Float(
        default=0,
        required=True,
    )
    sequence = fields.Integer(default=1)

    _name_src_uniq = name_uniq_index(
        message="The name of the Degree of Recruitment must be unique!",
    )
    _score_range = models.Constraint(
        "check(score >= 0 and score <= 1)",
        "Score should be between 0 and 100%",
    )
