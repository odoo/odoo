from odoo import fields, models


class MrpWorkcenter(models.Model):
    _name = "mrp.workcenter"
    _inherit = ["mrp.workcenter", "mixin.analytic"]

    expense_account_id = fields.Many2one(
        comodel_name="account.account",
        check_company=True,
        help="The expense is accounted for when the manufacturing order is marked as done. If not set, it is the expense account of the final product that will be used instead.",
    )


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    account_move_line_id = fields.Many2one(comodel_name="account.move.line")
