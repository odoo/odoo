from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ar_partner_tax_ids = fields.One2many(
        comodel_name="l10n_ar.partner.tax",
        inverse_name="partner_id",
        string="Argentinean Withholding Taxes",
    )
