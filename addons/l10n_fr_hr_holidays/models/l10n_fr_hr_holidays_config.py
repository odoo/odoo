from odoo import fields, models


class L10nFrHrHolidaysConfig(models.Model):
    _name = "l10n_fr_hr_holidays.config"
    _description = "A company's l10n fr hr holidays configuration"
    _inherit = ["mixin.company.config"]

    l10n_fr_reference_leave_type = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Company Paid Time Off Type",
    )
