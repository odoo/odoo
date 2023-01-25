from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_in_upi_id = fields.Char(string="UPI Id")

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            if company.account_fiscal_country_id.code == 'IN':
                company.display_invoice_amount_total_words = True
        return companies
