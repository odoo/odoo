from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _inverse_vat_disabled(self):
        super()._inverse_vat_disabled()
        for company in self:
            if company.account_fiscal_country_id.code != 'BE':
                continue
            # Disable all sales taxes and enable 0% Tax (Sale) and set it as default Sales Tax
            taxes_to_update = self.env['account.tax'].with_context(active_test=False, allowed_company_ids=company.ids).search(
                [('type_tax_use', '=', 'sale'), ('active', '=', company.vat_disabled)],
            )
            taxes_to_update.write({'active': not company.vat_disabled})
            ChartTemplate = self.env['account.chart.template'].with_company(company)
            tax_0_NA = ChartTemplate.ref('attn_VAT-OUT-00-NA-S', raise_if_not_found=False)
            tax_default_21 = ChartTemplate.ref('attn_VAT-OUT-21-L', raise_if_not_found=False)
            if company.vat_disabled and tax_0_NA:
                company.account_sale_tax_id = tax_0_NA
            elif not company.vat_disabled and tax_default_21:
                company.account_sale_tax_id = tax_default_21
            if tax_0_NA:
                tax_0_NA.write({'active': company.vat_disabled})
