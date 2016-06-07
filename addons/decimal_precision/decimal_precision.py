# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api
from odoo import SUPERUSER_ID


def get_precision(application):
    def change_digit(cr):
        env = api.Environment(cr, SUPERUSER_ID, {})
        DecimalPrecision = env['decimal.precision']
        res = DecimalPrecision.precision_get(application)
        return (16, res)
    return change_digit
