from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    subordinate_ids = fields.One2many(
        comodel_name="hr.employee",
        string="Subordinates",
        help="Direct and indirect subordinates",
        compute="_compute_subordinates",
        compute_sudo=True,
    )
    is_subordinate = fields.Boolean(
        compute="_compute_is_subordinate",
        search="_search_is_subordinate",
    )
