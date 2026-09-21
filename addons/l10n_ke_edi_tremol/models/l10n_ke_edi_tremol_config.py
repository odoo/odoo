from odoo import fields, models


class L10nKeEdiTremolConfig(models.Model):
    _name = "l10n_ke_edi_tremol.config"
    _description = "A company's l10n ke edi tremol configuration"
    _inherit = ["mixin.company.config"]

    l10n_ke_cu_proxy_address = fields.Char(
        string="Fiscal Device Proxy Address",
        default="http://localhost:8069",
        help="The address of the proxy server for the fiscal device.",
    )
