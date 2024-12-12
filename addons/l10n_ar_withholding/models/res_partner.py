from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ar_partner_tax_ids = fields.One2many(
        'l10n_ar.partner.tax',
        'partner_id',
        'Argentinean Withholding Taxes',
        domain=[('tax_id.l10n_ar_withholding_payment_type', '=', 'supplier')]
    )
    l10n_ar_partner_perception_ids = fields.One2many(
        'l10n_ar.partner.tax',
        'partner_id',
        'Argentinean Perception Taxes',
        domain=[('tax_id.type_tax_use', '=', 'sale')]
    )
