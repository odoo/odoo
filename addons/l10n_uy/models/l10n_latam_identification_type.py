from odoo import fields, models


class L10n_LatamIdentificationType(models.Model):
    _inherit = "l10n_latam.identification.type"

    l10n_uy_dgi_code = fields.Char(string="DGI Code")
