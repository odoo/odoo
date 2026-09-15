from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'AT':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_tax('account_tax_template_sales_not_subject_to_vat')

    def _get_default_vat_disabled_purchase_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'AT':
            return super()._get_default_vat_disabled_purchase_tax()
        return self._get_or_create_chart_template_tax('vat_disabled_purchase_nd')
