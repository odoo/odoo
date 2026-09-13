from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_ewaybill_username = fields.Char(
        string="E-Waybill Username",
        groups="base.group_system",
    )
    l10n_in_ewaybill_password = fields.Char(
        string="E-Waybill Password",
        groups="base.group_system",
    )
    l10n_in_ewaybill_auth_validity = fields.Datetime(
        string="E-Waybill Valid Until",
        groups="base.group_system",
    )
    l10n_in_ewaybill_feature = fields.Boolean(string="E-Waybill")

    def _l10n_in_ewaybill_token_is_valid(self):
        self.check_singleton()
        return (
            self.l10n_in_ewaybill_auth_validity
            and self.l10n_in_ewaybill_auth_validity > fields.Datetime.now()
        )
