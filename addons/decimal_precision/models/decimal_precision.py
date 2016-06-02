# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import tools
from openerp.osv import orm, fields


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
