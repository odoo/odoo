from odoo import fields, models
from odoo.addons.l10n_gr_edi.models.preferred_classification import (
    TAX_EXEMPTION_CATEGORY_SELECTION,
    VALID_TAX_CATEGORY_MAP,
)


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_gr_edi_default_tax_exemption_category = fields.Selection(
        selection=TAX_EXEMPTION_CATEGORY_SELECTION,
        string='Default Tax Exemption Category',
    )

    def _l10n_gr_edi_get_vat_category(self):
        self.ensure_one()
        chart_template = self.env['account.chart.template'].with_company(self.company_id)
        article_31_4_taxes = (
            chart_template.ref('l10n_gr_tax_s4_S_art31')
            | chart_template.ref('l10n_gr_tax_p4_S_art31')
        )
        # since category 10 shares the same vat rate with category 6 we need to handle it like that
        if self in article_31_4_taxes:
            return 10
        return VALID_TAX_CATEGORY_MAP[int(self.amount)]
