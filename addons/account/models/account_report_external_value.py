from odoo import fields, models


class AccountReportExternalValue(models.Model):
    _name = "account.report.external.value"
    _description = "Accounting Report External Value"
    _check_company_auto = True
    _order = "date, id"

    name = fields.Char(required=True)
    value = fields.Float(string="Numeric Value")
    text_value = fields.Char()
    date = fields.Date(required=True)

    target_report_expression_id = fields.Many2one(
        string="Target Expression",
        comodel_name="account.report.expression",
        required=True,
        index=True,
        ondelete="cascade",
    )
    target_report_line_id = fields.Many2one(
        string="Target Line", related="target_report_expression_id.report_line_id"
    )
    target_report_expression_label = fields.Char(
        string="Target Expression Label", related="target_report_expression_id.label"
    )
    report_country_id = fields.Many2one(
        string="Country", related="target_report_line_id.report_id.country_id"
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    carryover_origin_expression_label = fields.Char(string="Origin Expression Label")
    carryover_origin_report_line_id = fields.Many2one(
        string="Origin Line", comodel_name="account.report.line"
    )
