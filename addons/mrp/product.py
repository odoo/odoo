# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from tools.translate import _


class product_product(osv.osv):
    _inherit = "product.product"    

    def do_change_standard_price(self, cr, uid, ids, datas, context={}):
        #TODO : TO Check 
        res = super(product_product, self).do_change_standard_price(cr, uid, ids, datas, context=context)
        bom_obj = self.pool.get('mrp.bom')
        product_uom_obj = self.pool.get('product.uom')

        def _compute_price(bom):       
            print bom.product_id
            price = 0
#            if bom.bom_lines:
#                for sbom in bom.bom_lines:
#                    print "--->>>" , sbom.name
#                    price += _compute_price(sbom) * sbom.product_qty                    
#            else:
            parent_bom = bom_obj.search(cr, uid, [('bom_id', '=', False)])
            print "========", bom.product_id.name
            for p in parent_bom:
                test_obj = bom_obj.browse(cr, uid, p)
                print test_obj
                print "XXXXXXXXXXXXX", p, test_obj.child_ids
                
#            if no_child_bom and bom.id not in no_child_bom:
#                other_bom = bom_obj.browse(cr, uid, no_child_bom)[0]
#                if not other_bom.product_id.calculate_price:
#                    price += _compute_price(other_bom) * other_bom.product_qty
#                else:
#                    price += other_bom.product_id.standard_price
#            else:
#                price += bom.product_id.standard_price
#
#            if bom.routing_id:
#                for wline in bom.routing_id.workcenter_lines:
#                    wc = wline.workcenter_id
#                    cycle = wline.cycle_nbr
#                    hour = (wc.time_start + wc.time_stop + cycle * wc.time_cycle) *  (wc.time_efficiency or 1.0)
#                    price += wc.costs_cycle * cycle + wc.costs_hour * hour
#                    price = product_uom_obj._compute_price(cr, uid, bom.product_uom.id, price, bom.product_id.uom_id.id)
#            if bom.bom_lines:
#                self.write(cr, uid, [bom.product_id.id], {'standard_price' : price/bom.product_qty})
#            if bom.product_uom.id != bom.product_id.uom_id.id:
#                price = product_uom_obj._compute_price(cr, uid, bom.product_uom.id, price, bom.product_id.uom_id.id)
#            return price

        
        bom_ids = bom_obj.search(cr, uid, [('product_id', 'in', ids)])
        for bom in bom_obj.browse(cr, uid, bom_ids):
            _compute_price(bom)
        return res    
product_product()
