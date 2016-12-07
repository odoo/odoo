# coding: utf-8
# Copyright 2016 iterativo (https://www.iterativo.do) <info@iterativo.do>

from openerp import models, api, _


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.model
    def _get_default_bank_account_ids(self):
        return [
            {'acc_name': _('Cash'), 'account_type': 'cash'},
            {'acc_name': _('Caja Chica'), 'account_type': 'cash'},
            {'acc_name': _('Bank'), 'account_type': 'bank'}
            ]

    @api.model
    def default_get(self, fields):
        res = super(WizardMultiChartsAccounts, self).default_get(fields)
        if 'bank_account_ids' in fields:
            res.update({'bank_account_ids': self._get_default_bank_account_ids()})
        return res
