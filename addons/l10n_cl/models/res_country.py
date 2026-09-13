from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    l10n_cl_customs_code = fields.Char(string="Customs Code")
    l10n_cl_customs_name = fields.Char(string="Customs Name")
    l10n_cl_customs_abbreviation = fields.Char(string="Customs Abbreviation")
