from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ar_partner_tax_ids = fields.One2many(
        'l10n_ar.partner.tax',
        'partner_id',
        'Argentinean Withholding Taxes',
    )
