from odoo import models, fields
from odoo.addons import l10n_ar


class ResPartner(l10n_ar.ResPartner):

    l10n_ar_partner_tax_ids = fields.One2many(
        'l10n_ar.partner.tax',
        'partner_id',
        'Argentinean Withholding Taxes',
    )
