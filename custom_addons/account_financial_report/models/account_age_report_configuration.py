# Copyright 2023 Ernesto García
# Copyright 2023 Carolina Fernandez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountAgeReportConfiguration(models.Model):
    _name = "account.age.report.configuration"
    _description = "Model to set intervals for Age partner balance report"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, readonly=True
    )
    line_ids = fields.One2many(
        "account.age.report.configuration.line", "account_age_report_config_id"
    )

    @api.constrains("line_ids")
    def _check_line_ids(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(self.env._("Must complete Configuration Lines"))


class AccountAgeReportConfigurationLine(models.Model):
    _name = "account.age.report.configuration.line"
    _description = "Model to set interval lines for Age partner balance report"

    name = fields.Char(required=True)
    account_age_report_config_id = fields.Many2one("account.age.report.configuration")
    inferior_limit = fields.Integer()

    @api.constrains("inferior_limit")
    def _check_inferior_limit(self):
        for rec in self:
            if rec.inferior_limit <= 0:
                raise ValidationError(
                    self.env._("Inferior Limit must be greather than zero")
                )

    _sql_constraints = [
        (
            "unique_name_config_combination",
            "UNIQUE(name,account_age_report_config_id)",
            "Name must be unique per report configuration",
        )
    ]
