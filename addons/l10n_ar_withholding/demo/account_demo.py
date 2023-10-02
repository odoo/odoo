# -*- coding: utf-8 -*-
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, company=False):
        result = super()._post_load_demo_data(company)
        if company == self.env.ref('l10n_ar.company_ri', raise_if_not_found=False):
            self.env['account.tax'].search([('l10n_ar_withholding_payment_type', '!=', False)]).write({'amount_type': 'percent', 'amount' : 1})
            caba_wth = self.env.ref('account.%i_ri_tax_withholding_iibb_caba_applied' % company.id).id
            arba_wth = self.env.ref('account.%i_ri_tax_withholding_iibb_ba_applied' % company.id ).id
            self.env.ref('product.product_product_2').with_company(company.id).l10n_ar_supplier_withholding_taxes_ids = [(6, 0, [caba_wth])]
            self.env.ref('product.product_product_27').with_company(company.id).l10n_ar_supplier_withholding_taxes_ids = [(6, 0, [arba_wth])]
            self.env.ref('l10n_ar.product_product_telefonia').with_company(company.id).l10n_ar_supplier_withholding_taxes_ids = [(6, 0, [caba_wth, arba_wth])]
        return result
