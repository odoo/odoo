from odoo import fields, models


class ResPartnerTag(models.Model):
    _inherit = "res.partner.tag"

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="employee_tag_rel",
        column1="tag_id",
        column2="employee_id",
        string="Employees",
    )
