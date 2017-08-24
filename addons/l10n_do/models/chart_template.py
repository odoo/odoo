# coding: utf-8
# Copyright 2016 iterativo (https://www.iterativo.do) <info@iterativo.do>

from openerp import models, api, _


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.model
    def _get_default_bank_account_ids(self):
        if self.env.user.company_id.country_id and self.env.user.company_id.country_id.code.upper() == 'DO':
            return [
                    {'acc_name': _('Cash'), 'account_type': 'cash'},
                    {'acc_name': _('Caja Chica'), 'account_type': 'cash'},
                    {'acc_name': _('Bank'), 'account_type': 'bank'}
                ]
        return super(WizardMultiChartsAccounts, self)._get_default_bank_account_ids()
