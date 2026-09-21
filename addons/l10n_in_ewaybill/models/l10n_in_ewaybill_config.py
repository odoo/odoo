from odoo import fields, models


class L10nInEwaybillConfig(models.Model):
    _name = "l10n_in_ewaybill.config"
    _description = "A company's l10n in ewaybill configuration"
    _inherit = ["mixin.company.config"]

    l10n_in_ewaybill_username = fields.Char(
        string="E-Waybill Username",
        groups="base.group_system",
    )
    l10n_in_ewaybill_auth_validity = fields.Datetime(
        string="E-Waybill Valid Until",
        groups="base.group_system",
    )
    l10n_in_ewaybill_feature = fields.Boolean(string="E-Waybill")
