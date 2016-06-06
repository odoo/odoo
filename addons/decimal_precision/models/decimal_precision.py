# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import orm, fields
from openerp.modules.registry import RegistryManager

class decimal_precision(orm.Model):
    _name = 'decimal.precision'
    _columns = {
        'name': fields.char('Usage', select=True, required=True),
        'digits': fields.integer('Digits', required=True),
    }
    _defaults = {
        'digits': 2,
    }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', """Only one value can be defined for each given usage!"""),
    ]

    @tools.ormcache('application')
    def precision_get(self, cr, uid, application):
        cr.execute('select digits from decimal_precision where name=%s', (application,))
        res = cr.fetchone()
        return res[0] if res else 2

    def clear_cache(self, cr):
        """ Deprecated, use `clear_caches` instead. """
        self.clear_caches()

    def create(self, cr, uid, data, context=None):
        res = super(decimal_precision, self).create(cr, uid, data, context=context)
        self.clear_caches()
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(decimal_precision, self).unlink(cr, uid, ids, context=context)
        self.clear_caches()
        return res

    def write(self, cr, uid, ids, data, *args, **argv):
        res = super(decimal_precision, self).write(cr, uid, ids, data, *args, **argv)
        self.clear_caches()
        return res


def get_precision(application):
    def change_digit(cr):
        decimal_precision = openerp.registry(cr.dbname)['decimal.precision']
        res = decimal_precision.precision_get(cr, SUPERUSER_ID, application)
        return (16, res)
    return change_digit

class DecimalPrecisionFloat(orm.AbstractModel):
    """ Override qweb.field.float to add a `decimal_precision` domain option
    and use that instead of the column's own value if it is specified
    """
    _inherit = 'ir.qweb.field.float'


    def precision(self, cr, uid, field, options=None, context=None):
        dp = options and options.get('decimal_precision')
        if dp:
            return self.pool['decimal.precision'].precision_get(
                cr, uid, dp)

        return super(DecimalPrecisionFloat, self).precision(
            cr, uid, field, options=options, context=context)

class DecimalPrecisionTestModel(orm.Model):
    _name = 'decimal.precision.test'

    _columns = {
        'float': fields.float(),
        'float_2': fields.float(digits=(16, 2)),
        'float_4': fields.float(digits=(16, 4)),
    }
