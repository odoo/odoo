# -*- coding: utf-8 -*-
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

from osv import fields,osv
import tools
import ir
import pooler

class stock_location_path(osv.osv):
    _name = "stock.location.path"
    _columns = {
        'name': fields.char('Operation', size=64),
        'product_id' : fields.many2one('product.product', 'Products', ondelete='cascade', select=1),
        'location_from_id' : fields.many2one('stock.location', 'Source Location', ondelete='cascade', select=1),
        'location_dest_id' : fields.many2one('stock.location', 'Destination Location', ondelete='cascade', select=1),
        'delay': fields.integer('Delay (days)', help="Number of days to do this transition"),
        'auto': fields.selection(
            [('auto','Automatic Move'), ('manual','Manual Operation'),('transparent','Automatic No Step Added')],
            'Automatic Move',
            required=True, select=1,
            help="This is used to define paths the product has to follow within the location tree.\n" \
                "The 'Automatic Move' value will create a stock move after the current one that will be "\
                "validated automatically. With 'Manual Operation', the stock move has to be validated "\
                "by a worker. With 'Automatic No Step Added', the location is replaced in the original move."
            ),
    }
    _defaults = {
        'auto': lambda *arg: 'auto',
        'delay': lambda *arg: 1
    }
stock_location_path()

class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'path_ids': fields.one2many('stock.location.path', 'product_id',
            'Location Paths',
            help="These rules set the right path of the product in the "\
            "whole location tree.")
    }
product_product()

class stock_location(osv.osv):
    _inherit = 'stock.location'
    def chained_location_get(self, cr, uid, location, partner=None, product=None, context={}):
        if product:
            for path in product.path_ids:
                if path.location_from_id.id == location.id:
                    return path.location_dest_id, path.auto, path.delay
        return super(stock_location, self).chained_location_get(cr, uid, location, partner, product, context)
stock_location()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
