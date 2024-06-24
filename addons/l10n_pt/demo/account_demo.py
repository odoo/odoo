from odoo import api, models, fields


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company and company.account_fiscal_country_id.code == "PT":
            for series_type, preprefix in (("out_invoice", "INV"), ("out_refund", "RINV")):
                prefix = f'{preprefix}{fields.Date.context_today(self).year}'
                self.env['l10n_pt.at.series'].create({
                    'type': series_type,
                    'prefix': prefix,
                    'at_code': f"AT-{prefix}",
                    'company_id': company.id,
                })
        return demo_data
