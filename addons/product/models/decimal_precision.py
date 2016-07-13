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


class decimal_precision(osv.osv):
    _inherit = 'decimal.precision'

    def _check_main_currency_rounding(self, cr, uid, ids, context=None):
        cr.execute('SELECT id, digits FROM decimal_precision WHERE name like %s',('Account',))
        res = cr.fetchone()
        if res and len(res):
            account_precision_id, digits = res
            main_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
            for decimal_precision in ids:
                if decimal_precision == account_precision_id:
                    if float_compare(main_currency.rounding, 10 ** -digits, precision_digits=6) == -1:
                        return False
        return True

    _constraints = [
        (_check_main_currency_rounding, 'Error! You cannot define the decimal precision of \'Account\' as greater than the rounding factor of the company\'s main currency', ['digits']),
    ]
