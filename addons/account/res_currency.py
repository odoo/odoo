# -*- coding: utf-8 -*-

from openerp import models, api

"""Inherit res.currency to handle accounting date values when converting currencies"""

class res_currency_account(models.Model):
    _inherit = "res.currency"

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency):
        context = dict(self._context or {})
        rate = super(res_currency_account, self)._get_conversion_rate(from_currency, to_currency)
        #process the case where the account doesn't work with an outgoing currency rate method 'at date' but 'average'
        account = context.get('res.currency.compute.account')
        account_invert = context.get('res.currency.compute.account_invert')
        if account and account.currency_mode == 'average' and account.currency_id:
            query = self.env['account.move.line']._query_get()
            self._cr.execute('select sum(debit-credit),sum(amount_currency) from account_move_line l ' \
              'where l.currency_id=%s and l.account_id=%s and '+query, (account.currency_id.id, account.id,))
            tot1, tot2 = self._cr.fetchone()
            if tot2 and not account_invert:
                rate = float(tot1) / float(tot2)
            elif tot1 and account_invert:
                rate = float(tot2) / float(tot1)
        return rate
