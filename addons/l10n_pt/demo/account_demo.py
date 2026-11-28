from odoo import Command, api, models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data_move(self, company=False):
        """ Set taxes in demo moves, as Portuguese moves need at least one tax per move line. """
        data = super()._get_demo_data_move(company)

        if company and company.country_code == 'PT':
            european_countries = self.env.ref('base.europe').country_ids
            ChartTemplate = self.with_company(company)
            eu_sale_tax = ChartTemplate.ref('iva_pt_sale_eu_isenta')
            non_eu_sale_tax = ChartTemplate.ref('iva_pt_sale_non_eu_isenta')
            non_eu_purchase_tax = ChartTemplate.ref('iva_pt_purchase_non_eu_isenta')
            eu_purchase_tax = ChartTemplate.ref('iva_pt_purchase_eu_isenta')

            for move in data.values():
                if move['move_type'] == 'entry' or 'partner_id' not in move:
                    continue
                is_purchase = move['move_type'] in ['in_invoice', 'in_refund']
                if self.env.ref(move['partner_id']).country_id in european_countries:
                    tax = eu_purchase_tax if is_purchase else eu_sale_tax
                else:
                    tax = non_eu_purchase_tax if is_purchase else non_eu_sale_tax
                for line in move['invoice_line_ids']:
                    line[2]['tax_ids'] = [Command.set(tax.ids)]
        return data

    def _post_load_demo_data(self, company=False):
        # l10n_pt_certification is installed with this module and posts the PT demo company's
        # invoices itself, once their AT series and the exemption reasons of their taxes exist.
        if company == self.env.ref('base.demo_company_pt', raise_if_not_found=False) and self.env['ir.module.module'].sudo().search([
            ('name', '=', 'l10n_pt_certification'),
            ('state', '!=', 'installed'),
        ]):
            return None
        return super()._post_load_demo_data(company)
