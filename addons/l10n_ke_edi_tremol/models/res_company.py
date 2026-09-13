from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ke_cu_proxy_address = fields.Char(
        string="Fiscal Device Proxy Address",
        default="http://localhost:8069",
        help="The address of the proxy server for the fiscal device.",
    )
