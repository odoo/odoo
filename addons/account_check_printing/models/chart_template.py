# -*- coding: utf-8 -*-

from odoo import api, models


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        '''
        When system automatically creates journals of bank and cash type when CoA is being installed
        do not enable the `Check` payment method on bank journals of type `Cash`.

        '''
        bank_journals = super(WizardMultiChartsAccounts, self)._create_bank_journals_from_o2m(company, acc_template_ref)
        payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
        bank_journals.filtered(lambda journal: journal.type == 'cash').write({
            'outbound_payment_method_ids': [(3, payment_method_check.id)]
        })
        return bank_journals
