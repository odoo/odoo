# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _
from odoo.http import request


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def load_for_current_company(self, sale_tax_rate, purchase_tax_rate):
        """ When we load a chart of account and set a default tax, add this tax
        to every product """
        res = super().load_for_current_company(
            sale_tax_rate, purchase_tax_rate)

        if request and request.session.uid:
            current_user = self.env['res.users'].browse(request.uid)
            company = current_user.company_id
        else:
            # fallback to company of current user, most likely __system__
            # (won't work well for multi-company)
            company = self.env.user.company_id

        prod_templates = self.env['product.template'].search([])
        if company.account_sale_tax_id:
            prod_templates.write({
                'taxes_id': [(4, company.account_sale_tax_id.id)],
            })
        if company.account_purchase_tax_id:
            prod_templates.write({
                'supplier_taxes_id': [(4, company.account_purchase_tax_id.id)],
            })
        return res
