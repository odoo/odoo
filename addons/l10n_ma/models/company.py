from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            if company.account_fiscal_country_id.code == 'MA':
                company.display_invoice_amount_total_words = True
        return companies
