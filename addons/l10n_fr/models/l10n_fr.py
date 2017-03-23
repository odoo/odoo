# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    siret = fields.Char(string='SIRET', size=14)
    ape = fields.Char(string='APE')


class ChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journals = super(ChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict)
        if self.env.user.company_id.country_id == self.env.ref('base.fr'):
            for journal in journals:
                if journal['type'] in ['sale', 'purchase']:
                    journal['refund_sequence'] = True

        return journals
