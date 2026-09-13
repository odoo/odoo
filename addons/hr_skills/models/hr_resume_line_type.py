from odoo import fields, models


class HrResumeLineType(models.Model):
    _name = "hr.resume.line.type"
    _description = "Type of a resume line"
    _order = "sequence"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    is_course = fields.Boolean(
        string="Course",
        default=False,
    )
    resume_line_type_properties_definition = fields.PropertiesDefinition(
        string="Sections Properties"
    )
