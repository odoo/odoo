# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"
    
    @api.model
    def generate_equity_changes_journals(self, company=False):
        ''' Create Equity Changes Journal
        '''
        if company:
            company_objs = company
        else:
            company_objs = self.env['res.company'].sudo().search([])
        
        journal_code = 'ECRCR'
        for comp in company_objs:
            journals = self.env['account.journal'].sudo().search(
                [('company_id','=',comp.id),('code','=',journal_code)], limit=1)
            if not journals:
                journals = self.env['account.journal'].sudo().create({
                    'name': _('Equity Changes Correction Journal'),
                    'type': 'general',
                    'code': journal_code,
                    'company_id': comp.id,
                    'show_on_dashboard': False,
                    'color': False,
                    'sequence': 25
                })
            if not comp.aec_report_changes_impact_journal_id:
                comp.aec_report_changes_impact_journal_id = journals.id
            
    
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        res = super(AccountChartTemplate, self).generate_journals(acc_template_ref, company, journals_dict=journals_dict)
        self.generate_equity_changes_journals(company)
        
        return res
            
    