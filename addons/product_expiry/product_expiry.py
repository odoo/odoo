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
from osv import fields, osv
import pooler

class stock_production_lot(osv.osv):
    _name = 'stock.production.lot'
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
                product = pooler.get_pool(cr.dbname).get('product.product').browse(
                    cr, uid, context['product_id'])
                duration = getattr(product, dtype)
                # set date to False when no expiry time specified on the product
                date = duration and (datetime.datetime.today()
                    + datetime.timedelta(days=duration))
            return date and date.strftime('%Y-%m-%d')
        return calc_date

    _columns = {
        'life_date': fields.date('End of Life Date',
            help='The date the lot may become dangerous and should not be consumed.'),
        'use_date': fields.date('Best before Date',
            help='The date the lot starts deteriorating without becoming dangerous.'),
        'removal_date': fields.date('Removal Date',
            help='The date the lot should be removed.'),
        'alert_date': fields.date('Alert Date'),
    }

    _defaults = {
   #     'life_date': _get_date('life_time'),
   #     'use_date': _get_date('use_time'),
   #     'removal_date': _get_date('removal_time'),
   #     'alert_date': _get_date('alert_time'),
    }
stock_production_lot()

class product_product(osv.osv):
    _inherit = 'product.product'
    _name = 'product.product'
    _columns = {
        'life_time': fields.integer('Product lifetime',
            help='The number of days before a production lot may become dangerous and should not be consumed.'),
        'use_time': fields.integer('Product usetime',
            help='The number of days before a production lot starts deteriorating without becoming dangerous.'),
        'removal_time': fields.integer('Product removal time',
            help='The number of days before a production lot should be removed.'),
        'alert_time': fields.integer('Product alert time'),
    }
product_product()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

