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
        comodel_name="account.report.expression",
        string="Target Expression",
        index=True,
        required=True,
        ondelete="cascade",
    )
    target_report_line_id = fields.Many2one(
        related="target_report_expression_id.report_line_id",
        string="Target Line",
    )
    target_report_expression_label = fields.Char(
        related="target_report_expression_id.label",
        string="Target Expression Label",
    )
    report_country_id = fields.Many2one(
        related="target_report_line_id.report_id.country_id",
        string="Country",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    carryover_origin_expression_label = fields.Char(string="Origin Expression Label")
    carryover_origin_report_line_id = fields.Many2one(
        comodel_name="account.report.line",
        string="Origin Line",
    )
