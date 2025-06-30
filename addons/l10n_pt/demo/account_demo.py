from odoo import api, Command, models, fields


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company and company.account_fiscal_country_id.code == "PT":
            # Create demo AT series. Demo data contains moves from the current and previous month,
            # which can occasionally fall in the year prior
            if fields.Date.context_today(self).month == 1:
                years = (fields.Date.context_today(self).year, fields.Date.context_today(self).year - 1)
            else:
                years = (fields.Date.context_today(self).year,)
            sale_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'sale'),
            ], limit=1)
            bank_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'sale'),
            ], limit=1)
            for year in years:
                self.env['l10n_pt.at.series'].create([{
                    'name': str(year),
                    'company_id': company.id,
                    'training_series': True,
                    'sale_journal_id': sale_journal.id,
                    'payment_journal_id': bank_journal.id,
                    'at_series_line_ids': [
                        Command.create({
                            'type': series_type,
                            'prefix': prefix,
                            'at_code': f'AT-{prefix}{year}',
                        })
                        for series_type, prefix in (('out_invoice', 'INV'), ('out_refund', 'RINV'), ('payment_receipt', 'RG'))
                    ]
                }])
        return demo_data

    @api.model
    def _get_demo_data_move(self, company=False):
        """ Set taxes in demo moves, as Portuguese moves need at least one tax per move line. """
        data = super()._get_demo_data_move(company)

        if company.country_code == 'PT':
            european_countries = self.env.ref('base.europe').country_ids
            eu_sale_tax = self.env['account.chart.template'].ref('iva_pt_sale_eu_isenta')
            non_eu_sale_tax = self.env['account.chart.template'].ref('iva_pt_sale_non_eu_isenta')
            non_eu_purchase_tax = self.env['account.chart.template'].ref('iva_pt_purchase_non_eu_isenta')
            eu_purchase_tax = self.env['account.chart.template'].ref('iva_pt_purchase_eu_isenta')

            for move in data.values():
                if move['move_type'] == 'entry' or 'partner_id' not in move:
                    continue
                if self.env.ref(move['partner_id']).country_id in european_countries:
                    for line in move['invoice_line_ids']:
                        line[2]['tax_ids'] = [Command.set(eu_sale_tax.ids)] if move['move_type'] in ['in_invoice', 'in_refund'] else [Command.set(eu_purchase_tax.ids)]
                else:
                    for line in move['invoice_line_ids']:
                        line[2]['tax_ids'] = [Command.set(non_eu_sale_tax.ids)] if move['move_type'] in ['in_invoice', 'in_refund'] else [Command.set(non_eu_purchase_tax.ids)]
        return data
