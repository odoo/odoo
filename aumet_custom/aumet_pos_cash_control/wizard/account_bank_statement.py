# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import float_is_zero
from odoo.tools import float_compare, float_round, float_repr
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import UserError, ValidationError

import time
import math
import base64
import re


class AccountBankStmtCashWizard(models.Model):
    _inherit = 'account.bank.statement.cashbox'

    @api.model
    def default_get(self, fields):
        # record_ids = self._context.get('active_ids')
        result = super(AccountBankStmtCashWizard, self).default_get(fields)

        # if 'cashbox_lines_ids' in fields:
        cashbox_lines_ids = [
                                (0, 0, {
                                    'number': 1,
                                }),
                                (0, 0, {
                                    'number': 5,
                                }),(0, 0, {
                                    'number': 10,
                                }),
                                (0, 0, {
                                    'number': 20,
                                }),(0, 0, {
                                    'number': 50,
                                }),
                            ]
        result['cashbox_lines_ids'] = cashbox_lines_ids

        return result
