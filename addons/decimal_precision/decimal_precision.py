# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp import SUPERUSER_ID


def get_precision(application):
    def change_digit(cr):
        decimal_precision = openerp.registry(cr.dbname)['decimal.precision']
        res = decimal_precision.precision_get(cr, SUPERUSER_ID, application)
        return (16, res)
    return change_digit
