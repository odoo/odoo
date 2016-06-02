# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import orm, fields


class DecimalPrecisionTestModel(orm.Model):
    _name = 'decimal.precision.test'

    _columns = {
        'float': fields.float(),
        'float_2': fields.float(digits=(16, 2)),
        'float_4': fields.float(digits=(16, 4)),
    }
