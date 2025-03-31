from odoo import fields, models
from odoo.addons.l10n_gr_edi.models.preferred_classification import TAX_EXEMPTION_CATEGORY_SELECTION


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_gr_edi_default_tax_exemption_category = fields.Selection(
        selection=TAX_EXEMPTION_CATEGORY_SELECTION,
        string='MyDATA Default Tax Exemption Category',
    )
