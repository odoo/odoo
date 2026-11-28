from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mq')
    def _get_mq_template_data(self):
        return {
            'name': self.env._('General Accounting Plan'),
            'code_digits': '6',
            'parent': 'fr_comp',
        }

    @template('mq', 'account.account')
    def _get_mq_account_account(self):
        return super()._get_account_account('fr_comp')

    @template('mq', 'account.tax')
    def _get_mq_account_tax(self):
        account_tax = super()._get_account_tax('fr_comp')
        for xmlid, tax_data in self._parse_csv('mq', 'account.tax').items():
            account_tax[xmlid].update(tax_data)
        return account_tax

    def _deref_account_tags(self, template_code, tax_data):
        if template_code == 'mq':
            template_code = 'fr_comp'
        return super()._deref_account_tags(template_code, tax_data)

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code == 'mq':
            if not company.account_sale_tax_id.active:
                company.account_sale_tax_id = self.ref('tva_specifique')
            if not company.account_purchase_tax_id.active:
                company.account_purchase_tax_id = self.ref('tva_acq_specifique')
