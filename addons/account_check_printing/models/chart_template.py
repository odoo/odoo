# -*- coding: utf-8 -*-

from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _create_bank_journals(self, company, acc_template_ref):
        '''
        When system automatically creates journals of bank and cash type when CoA is being installed
        do not enable the `Check` payment method on bank journals of type `Cash`.

        '''
        bank_journals = super(AccountChartTemplate, self)._create_bank_journals(company, acc_template_ref)
        payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
        bank_journals.filtered(lambda journal: journal.type == 'cash').write({
            'outbound_payment_method_ids': [(3, payment_method_check.id)]
        })
        return bank_journals
