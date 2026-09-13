from odoo import fields, models


class ResBank(models.Model):
    _name = "res.bank"
    _inherit = ["res.bank", "mixin.fiscal.country.codes"]

    l10n_mx_edi_code = fields.Char(
        string="ABM Code",
        help="Three-digit number assigned by the ABM to identify banking "
        "institutions (ABM is an acronym for Asociación de Bancos de México)",
    )


class ResPartnerBank(models.Model):
    _name = "res.partner.bank"
    _inherit = ["res.partner.bank", "mixin.fiscal.country.codes"]

    l10n_mx_edi_clabe = fields.Char(
        string="CLABE",
        help="Standardized banking cipher for Mexico. More info "
        "wikipedia.org/wiki/CLABE",
    )
