from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'SI':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_tax('l10n_si_vat_sale_not_subject')

    def _get_default_vat_disabled_purchase_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'SI':
            return super()._get_default_vat_disabled_purchase_tax()
        return self._get_or_create_chart_template_tax('gd_taxp_nr_2')
