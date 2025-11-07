from odoo import Command, api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self, company=False):
        """ Set taxes in demo moves, as Portuguese moves need at least one tax per move line. """
        data = super()._get_demo_data_move(company)

        if company and company.country_code == 'PT':
            european_countries = self.env.ref('base.europe').country_ids
            eu_sale_tax = self.env['account.chart.template'].with_company(company).ref('iva_pt_sale_eu_isenta')
            non_eu_sale_tax = self.env['account.chart.template'].with_company(company).ref('iva_pt_sale_non_eu_isenta')
            non_eu_purchase_tax = self.env['account.chart.template'].with_company(company).ref('iva_pt_purchase_non_eu_isenta')
            eu_purchase_tax = self.env['account.chart.template'].with_company(company).ref('iva_pt_purchase_eu_isenta')

            for move in data.values():
                if move['move_type'] == 'entry' or 'partner_id' not in move:
                    continue
                if self.env.ref(move['partner_id']).country_id in european_countries:
                    tax = eu_sale_tax if move['move_type'] in ['in_invoice', 'in_refund'] else eu_purchase_tax
                else:
                    tax = non_eu_sale_tax if move['move_type'] in ['in_invoice', 'in_refund'] else non_eu_purchase_tax
                # set tax in each line
                for line in move['invoice_line_ids']:
                    line[2]['tax_ids'] = [Command.set(tax.ids)]
        return data

    def _post_load_demo_data(self, company=False):
        if not (
            company == self.env.ref('base.demo_company_pt', raise_if_not_found=False)
            and self.env['ir.module.module'].sudo().search([
                ('name', '=', 'l10n_pt_certification'),
                ('state', '!=', 'installed'),
            ])
        ):
            return super()._post_load_demo_data(company)
