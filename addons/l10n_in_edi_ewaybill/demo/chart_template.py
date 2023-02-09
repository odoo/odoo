from odoo import models, api, Command


class AccountChartTemplate(models.Model):
    _inherit='account.chart.template'

    @api.model
    def _get_demo_data(self):
        if self.env.company == self.env.ref('l10n_in_edi_ewaybill.demo_company_in_ewaybill'):
            val = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', self.env.ref('l10n_in_edi_ewaybill.demo_company_in_ewaybill').id)])
            a = {'edi_format_ids': [Command.unlink(self.env.ref('l10n_in_edi.edi_in_einvoice_json_1_03').id)]}
            val.write(a)
        return super()._get_demo_data()
