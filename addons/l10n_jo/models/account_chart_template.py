from odoo import models, _, api


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """ If JORDAN chart, we add one new journal Tax Adjustment"""
        if self == self.env.ref('l10n_jo.jordan_chart_template_standard'):
            if not journals_dict:
                journals_dict = []
            journals_dict.extend(
                [{"name": "Tax Adjustments", "company_id": company.id, "code": "TA", "type": "general", "sequence": 1,
                  "favorite": True}])
        return super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
    
    @api.model
    def _get_default_bank_journals_data(self):
        if self == self.env.ref('l10n_jo.jordan_chart_template_standard'):
            return [
                {'acc_name': _('Cash'), 'account_type': 'cash', 'default_account_id': self.env.ref('l10n_jo.jo_account_100108')},
                {'acc_name': _('Bank'), 'account_type': 'bank', 'default_account_id': self.env.ref('l10n_jo.jo_account_100105')}
            ]
        return super()._get_default_bank_journals_data()
    
    def _create_bank_journals(self, company, acc_template_ref):
        '''
        If JORDAN chart, pass default account for bank and cash journal
        to prevent auto account creation
        '''
        if self == self.env.ref('l10n_jo.jordan_chart_template_standard'):
            self.ensure_one()
            bank_journals = self.env['account.journal']
            for acc in self._get_default_bank_journals_data():
                bank_journals += self.env['account.journal'].create({
                    'name': acc['acc_name'],
                    'type': acc['account_type'],
                    'company_id': company.id,
                    'currency_id': acc.get('currency_id', self.env['res.currency']).id,
                    'sequence': 10,
                    'default_account_id': acc_template_ref.get(acc['default_account_id']).id  # pass default account
                })
            return bank_journals
        return super()._create_bank_journals(company, acc_template_ref)
