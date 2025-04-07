from odoo import api, Command, models, fields


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _get_demo_data(self, company=False):
        demo_data = super()._get_demo_data(company)
        if company and company.account_fiscal_country_id.code == "PT":
            # Demo data contains moves from the current and previous month, which can occasionally fall in the year prior
            if fields.Date.context_today(self).month == 1:
                years = (fields.Date.context_today(self).year, fields.Date.context_today(self).year - 1)
            else:
                years = (fields.Date.context_today(self).year,)
            for year in years:
                series = self.env['l10n_pt.at.series'].create({
                    'name': str(year),
                    'company_id': company.id,
                    'training_series': True,
                    'sale_journal_id': self.env['account.journal'].search([*self.env['account.journal']._check_company_domain(company),('type', '=', 'sale')], limit=1).id,
                })
                series.write({
                    'at_series_line_ids': [
                        Command.create({
                            'type': series_type,
                            'prefix': prefix,
                            'at_code': f'AT-{prefix}{year}',
                        })
                        for series_type, prefix in (("out_invoice", "INV"), ("out_refund", "RINV"))
                    ]
                })
        return demo_data

    @api.model
    def _get_demo_data_move(self, company=False):
        """ Set taxes in demo moves, as Portuguese moves need at least one tax per move line. """
        data = super()._get_demo_data_move(company)

        if company.account_fiscal_country_id.code == 'PT':
            eu_sale_tax = self.env['account.chart.template'].ref('iva_pt_sale_eu_isenta')
            non_eu_sale_tax = self.env['account.chart.template'].ref('iva_pt_sale_non_eu_isenta')
            non_eu_purchase_tax = self.env['account.chart.template'].ref('iva_pt_purchase_non_eu_isenta')

            data['demo_invoice_1']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_02', 'quantity': 5, 'tax_ids': [Command.set(non_eu_sale_tax.ids)]}),
                Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5, 'tax_ids': [Command.set(non_eu_sale_tax.ids)]}),
            ]
            data['demo_invoice_2']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
                Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 20, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
            ]
            data['demo_invoice_3']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
                Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
            ]
            data['demo_invoice_followup']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_02', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
                Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
            ]
            data['demo_invoice_5']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.product_delivery_01', 'quantity': 1, 'tax_ids': [Command.set(non_eu_purchase_tax.ids)]}),
                Command.create({'product_id': 'product.product_order_01', 'quantity': 5, 'tax_ids': [Command.set(non_eu_purchase_tax.ids)]}),
            ]
            data['demo_move_auto_reconcile_1']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5, 'tax_ids': [Command.set(non_eu_sale_tax.ids)]}),
            ]
            data['demo_move_auto_reconcile_2']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_02', 'quantity': 5, 'tax_ids': [Command.set(non_eu_sale_tax.ids)]}),
            ]
            data['demo_move_auto_reconcile_3']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.product_delivery_01', 'quantity': 1, 'tax_ids': [Command.set(non_eu_purchase_tax.ids)]}),
                Command.create({'product_id': 'product.product_order_01', 'quantity': 5, 'tax_ids': [Command.set(non_eu_purchase_tax.ids)]}),
            ]
            data['demo_move_auto_reconcile_5']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_02', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
                Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
            ]
            data['demo_move_auto_reconcile_6']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
                Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 20, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
            ]
            data['demo_move_auto_reconcile_7']['invoice_line_ids'] = [
                Command.create({'product_id': 'product.consu_delivery_01', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
                Command.create({'product_id': 'product.consu_delivery_03', 'quantity': 5, 'tax_ids': [Command.set(eu_sale_tax.ids)]}),
            ]
        return data
