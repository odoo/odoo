from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_ewaybill_username = fields.Char("E-Waybill (IN) Username", groups="base.group_system")
    l10n_in_ewaybill_password = fields.Char("E-Waybill (IN) Password", groups="base.group_system")
    l10n_in_ewaybill_auth_validity = fields.Datetime("E-Waybill (IN) Valid Until", groups="base.group_system")
    l10n_in_ewaybill_production_env = fields.Boolean(
        string="E-Waybill (IN) Is production OSE environment",
        help="Enable the use of production credentials",
        groups="base.group_system",
    )

    def _l10n_in_ewaybill_token_is_valid(self):
        self.ensure_one()
        return (
            self.l10n_in_ewaybill_auth_validity
            and self.l10n_in_ewaybill_auth_validity > fields.Datetime.now()
        )
