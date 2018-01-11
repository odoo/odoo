# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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

    @tools.ormcache(skiparg=3)
    def precision_get(self, cr, uid, application):
        cr.execute('select digits from decimal_precision where name=%s', (application,))
        res = cr.fetchone()
        return res[0] if res else 2

    def clear_cache(self, cr):
        """clear cache and update models. Notify other workers to restart their registry."""
        self.precision_get.clear_cache(self)
        RegistryManager.signal_registry_change(cr.dbname)

    def create(self, cr, uid, data, context=None):
        res = super(decimal_precision, self).create(cr, uid, data, context=context)
        self.clear_cache(cr)
        return res

    def unlink(self, cr, uid, ids, context=None):
        res = super(decimal_precision, self).unlink(cr, uid, ids, context=context)
        self.clear_cache(cr)
        return res

    def write(self, cr, uid, ids, data, *args, **argv):
        res = super(decimal_precision, self).write(cr, uid, ids, data, *args, **argv)
        self.clear_cache(cr)
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
