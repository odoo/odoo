# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import time

import openerp
from openerp import api, tools, SUPERUSER_ID
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import psycopg2

import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round, float_compare
from openerp.exceptions import UserError
from openerp.exceptions import except_orm


class res_currency(osv.osv):
    _inherit = 'res.currency'

    def _check_main_currency_rounding(self, cr, uid, ids, context=None):
        cr.execute('SELECT digits FROM decimal_precision WHERE name like %s',('Account',))
        digits = cr.fetchone()
        if digits and len(digits):
            digits = digits[0]
            main_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
            for currency_id in ids:
                if currency_id == main_currency.id:
                    if float_compare(main_currency.rounding, 10 ** -digits, precision_digits=6) == -1:
                        return False
        return True

    _constraints = [
        (_check_main_currency_rounding, 'Error! You cannot define a rounding factor for the company\'s main currency that is smaller than the decimal precision of \'Account\'.', ['rounding']),
    ]
