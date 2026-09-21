from odoo import fields, models


class L10nInEdiConfig(models.Model):
    _name = "l10n_in_edi.config"
    _description = "A company's l10n in edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_in_edi_feature = fields.Boolean(string="Indian E-Invoicing")
    l10n_in_edi_username = fields.Char(
        string="E-invoice (IN) Username",
        groups="base.group_system",
    )
    l10n_in_edi_token_validity = fields.Datetime(
        string="E-invoice (IN) Valid Until",
        groups="base.group_system",
    )
