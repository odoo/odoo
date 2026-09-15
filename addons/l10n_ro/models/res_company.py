from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'RO':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_tax('tvatine')

    def _get_default_vat_disabled_purchase_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'RO':
            return super()._get_default_vat_disabled_purchase_tax()
        return self._get_or_create_chart_template_tax('tva_vat_disabled_nd')
