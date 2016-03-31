# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

import openerp
from openerp import api, models
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
        context = dict(context or {})
        context['product_id'] = vals.get('product_id', context.get('default_product_id'))
        return super(stock_production_lot, self).create(cr, uid, vals, context=context)

    _defaults = {
        'life_date': _get_date('life_time'),
        'use_date': _get_date('use_time'),
        'removal_date': _get_date('removal_time'),
        'alert_date': _get_date('alert_time'),
    }


# Onchange added in new api to avoid having to change views
class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.onchange('product_id')
    def _onchange_product(self):
        defaults = self.with_context(
            product_id=self.product_id.id).default_get(
                ['life_date', 'use_date', 'removal_date', 'alert_date'])
        for field, value in defaults.items():
            setattr(self, field, value)


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

    def apply_removal_strategy(self, cr, uid, qty, move, ops=False, domain=None, removal_strategy='fifo', context=None):
        if removal_strategy == 'fefo':
            order = 'removal_date, in_date, id'
            return self._quants_get_order(cr, uid, qty, move, ops=ops, domain=domain, orderby=order, context=context)
        return super(stock_quant, self).apply_removal_strategy(cr, uid, qty, move, ops=ops, domain=domain,
                                                               removal_strategy=removal_strategy, context=context)


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
