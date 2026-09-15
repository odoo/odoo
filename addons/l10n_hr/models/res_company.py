from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'HR':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_tax('VAT_S_NOT_SUBJECT_HR')

    def _get_default_vat_disabled_purchase_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'HR':
            return super()._get_default_vat_disabled_purchase_tax()
        return self._get_or_create_chart_template_tax('VAT_P_DISABLED_ND_HR')
