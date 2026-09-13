from odoo import fields, models

from odoo.addons.account.models.account_report import (
    FIGURE_TYPE_SELECTION_VALUES,
)


class AccountReportColumn(models.Model):
    _name = "account.report.column"
    _description = "Accounting Report Column"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    expression_label = fields.Char(required=True)
    sequence = fields.Integer()
    report_id = fields.Many2one(
        comodel_name="account.report",
        index="btree_not_null",
        required=True,
        ondelete="cascade",
    )
    sortable = fields.Boolean()
    figure_type = fields.Selection(
        selection=FIGURE_TYPE_SELECTION_VALUES,
        default="monetary",
        required=True,
    )
    blank_if_zero = fields.Boolean(
        string="Blank if Zero",
        help="When checked, 0 values will not show in this column.",
    )
    custom_audit_action_id = fields.Many2one(comodel_name="ir.actions.act_window")
