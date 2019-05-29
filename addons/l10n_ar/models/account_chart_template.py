# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company,
                              journals_dict=None):
        """ If argentinian chart, we don't create sales journal as we need more
        data to create it properly
        """
        res = super(
            AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)

        if company.country_id == self.env.ref('base.ar'):
            res = [item for item in res if item.get('type') != 'sale']
        return res
