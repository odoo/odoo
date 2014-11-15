# -*- coding: utf-8 -*-

from openerp import models, api

"""Inherit res.currency to handle accounting date values when converting currencies"""

class res_currency_account(models.Model):
    _inherit = "res.currency"

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency):
        context = dict(self._context or {})
        rate = super(res_currency_account, self)._get_conversion_rate(from_currency, to_currency)
        return rate
