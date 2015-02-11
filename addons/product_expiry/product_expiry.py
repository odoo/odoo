# -*- coding: utf-8 -*-

import datetime
from openerp import api, fields, models 


class stock_production_lot(models.Model):
    _inherit = 'stock.production.lot'
    
    @api.model
    def _get_date(self, dtype):
        """Return a function to compute the limit date for this type"""
        def calc_date(dtype):
            """Compute the limit date for a given date"""
            if not self._context.get('product_id', False):
                date = False
            else:
                product = self.env['product.product'].browse(self._context.get('product_id'))
                duration = getattr(product, dtype)
                # set date to False when no expiry time specified on the product
                date = duration and (datetime.datetime.today()
                    + datetime.timedelta(days=duration))
            return date and date.strftime('%Y-%m-%d %H:%M:%S') or False
        return calc_date(dtype)

    life_date = fields.Datetime('End of Life Date', default=lambda self: self._get_date('life_time'),
        help='This is the date on which the goods with this Serial Number may become dangerous and must not be consumed.')
    use_date = fields.Datetime('Best before Date', default=lambda self: self._get_date('use_time'),
        help='This is the date on which the goods with this Serial Number start deteriorating, without being dangerous yet.')
    removal_date = fields.Datetime('Removal Date', default=lambda self: self._get_date('removal_time'), 
        help='This is the date on which the goods with this Serial Number should be removed from the stock.')
    alert_date = fields.Datetime('Alert Date', default=lambda self: self._get_date('alert_time'), 
        help="This is the date on which an alert should be notified about the goods with this Serial Number.")
            
    # Assign dates according to products data
    @api.model
    def create(self, vals):
        lot_rec = super(stock_production_lot, self).create(vals)
        towrite = []
        for f in ('life_date', 'use_date', 'removal_date', 'alert_date'):
            if not getattr(lot_rec, f):
                towrite.append(f)
        lot_rec.write(self.with_context({'product_id': lot_rec.product_id.id}).default_get(towrite))
        return lot_rec

class stock_quant(models.Model):
    _inherit = 'stock.quant'

    removal_date = fields.Datetime(string='Removal Date', related='lot_id.removal_date',
            store=True)
            
    @api.model
    def apply_removal_strategy(self, location, product, qty, domain, removal_strategy):
        if removal_strategy == 'fefo':
            order = 'removal_date, in_date, id'
            return self._quants_get_order(location, product, qty, domain, order)
        return super(stock_quant, self).apply_removal_strategy(location, product, qty, domain, removal_strategy)


class product_product(models.Model):
    _inherit = 'product.template'
    
    life_time = fields.Integer(string='Product Life Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods may become dangerous and must not be consumed.')
    use_time = fields.Integer(string='Product Use Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods starts deteriorating, without being dangerous yet.')
    removal_time = fields.Integer(string='Product Removal Time',
            help='When a new a Serial Number is issued, this is the number of days before the goods should be removed from the stock.')
    alert_time = fields.Integer(string='Product Alert Time',
            help='When a new a Serial Number is issued, this is the number of days before an alert should be notified.')
    
