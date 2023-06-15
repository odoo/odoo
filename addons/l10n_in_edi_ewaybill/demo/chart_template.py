# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, Command


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @api.model
    def _get_demo_data(self, company=False):
        company = company or self.env.company
        """We need to deactivate einvoice here, as we can not send e-invoice and e-waybill in the same demo company"""
        if company == self.env.ref('l10n_in_edi_ewaybill.demo_company_in_ewaybill'):
            sales_journals = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'sale'),
            ])
            sales_journals.write({'edi_format_ids': [Command.unlink(self.env.ref('l10n_in_edi.edi_in_einvoice_json_1_03').id)]})
        return super()._get_demo_data(company)
