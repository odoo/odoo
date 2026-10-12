from odoo import api, models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_tr_default_sales_return_account_id = fields.Many2one(
        comodel_name="account.account",
        company_dependent=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)

        for product in products:
            if product.company_id.country_code == 'TR':
                ChartTemplate = self.env['account.chart.template'].with_company(product.company_id)
                return_account = ChartTemplate.ref('tr610', raise_if_not_found=False)
                product.l10n_tr_default_sales_return_account_id = return_account

        return products
