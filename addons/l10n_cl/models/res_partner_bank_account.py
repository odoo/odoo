from odoo import fields, models


class ResBank(models.Model):
    _name = "res.bank"
    _inherit = ["res.bank", "mixin.fiscal.country.codes"]

    l10n_cl_sbif_code = fields.Char(
        string="Cod. SBIF",
        size=10,
    )
