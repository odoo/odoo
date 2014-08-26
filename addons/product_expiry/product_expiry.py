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

import datetime

import openerp
from openerp.osv import fields, osv

class stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'

    def _get_date(dtype):
        """Return a function to compute the limit date for this type"""
        def calc_date(self, cr, uid, context=None):
            """Compute the limit date for a given date"""
            if context is None:
                context = {}
            if not context.get('product_id', False):
                date = False
            else:
                product = openerp.registry(cr.dbname)['product.product'].browse(
                    cr, uid, context['product_id'])
                duration = getattr(product, dtype)
                # set date to False when no expiry time specified on the product
                date = duration and (datetime.datetime.today()
                    + datetime.timedelta(days=duration))
            return date and date.strftime('%Y-%m-%d %H:%M:%S') or False
        return calc_date

    _columns = {
        'life_date': fields.datetime('End of Life Date',
            help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.'),
        'use_date': fields.datetime('Best before Date',
            help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.'),
        'removal_date': fields.datetime('Removal Date',
            help='This is the date on which the goods with this Serial Number should be removed from the stock.'),
        'alert_date': fields.datetime('Alert Date',
            help="This is the date on which an alert should be notified about the goods with this Serial Number."),
    }
    # Assign dates according to products data
    def create(self, cr, uid, vals, context=None):
        newid = super(stock_production_lot, self).create(cr, uid, vals, context=context)
        obj = self.browse(cr, uid, newid, context=context)
        towrite = []
        for f in ('life_date', 'use_date', 'removal_date', 'alert_date'):
            if not getattr(obj, f):
                towrite.append(f)
        context = dict(context or {})
        context['product_id'] = obj.product_id.id
        self.write(cr, uid, [obj.id], self.default_get(cr, uid, towrite, context=context))
        return newid

    _defaults = {
        'life_date': _get_date('life_time'),
        'use_date': _get_date('use_time'),
        'removal_date': _get_date('removal_time'),
        'alert_date': _get_date('alert_time'),
    }


class stock_quant(osv.osv):
    _inherit = 'stock.quant'

    def _get_quants(self, cr, uid, ids, context=None):
        return self.pool.get('stock.quant').search(cr, uid, [('lot_id', 'in', ids)], context=context)

    _columns = {
        'removal_date': fields.related('lot_id', 'removal_date', type='datetime', string='Removal Date',
            store={
                'stock.quant': (lambda self, cr, uid, ids, ctx: ids, ['lot_id'], 20),
                'stock.production.lot': (_get_quants, ['removal_date'], 20),
            }),
    }

    def apply_removal_strategy(self, cr, uid, location, product, qty, domain, removal_strategy, context=None):
        if removal_strategy == 'fefo':
            order = 'removal_date, in_date, id'
            return self._quants_get_order(cr, uid, location, product, qty, domain, order, context=context)
        return super(stock_quant, self).apply_removal_strategy(cr, uid, location, product, qty, domain, removal_strategy, context=context)


class product_product(osv.osv):
    _inherit = 'product.template'
    _columns = {
        'life_time': fields.integer('Product Life Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods may become dangerous and must not be consumed.'),
        'use_time': fields.integer('Product Use Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods starts deteriorating, without being dangerous yet.'),
        'removal_time': fields.integer('Product Removal Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods should be removed from the stock.'),
        'alert_time': fields.integer('Product Alert Time',
            help='When a new a Serial Number is issued, this is the number of days before an alert should be notified.'),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
