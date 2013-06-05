##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP S.A. (<http://www.openerp.com>).
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

from openerp.osv import fields
from openerp.osv import osv




class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'
    


    _columns = {
        'calculate_price': fields.boolean('Compute standard price', help="Check this box if the standard price must be computed from the BoM."),
    }

    _defaults = {
        'calculate_price': lambda w,x,y,z: False,
    }

    def compute_price(self, cr, uid, ids, *args):
        proxy = self.pool.get('mrp.bom')
        for prod_id in ids:
            bom_ids = proxy.search(cr, uid, [('product_id', '=', prod_id)])
            if bom_ids:
                for bom in proxy.browse(cr, uid, bom_ids):
                    self._calc_price(cr, uid, bom)
        return True
                    
    def _calc_price(self, cr, uid, bom):
        if not bom.product_id.calculate_price:
            return bom.product_id.standard_price
        else:
            price = 0
            if bom.bom_lines:
                for sbom in bom.bom_lines:
                    my_qty = sbom.bom_lines and 1.0 or sbom.product_qty
                    price += self._calc_price(cr, uid, sbom) * my_qty
            else:
                bom_obj = self.pool.get('mrp.bom')
                no_child_bom = bom_obj.search(cr, uid, [('product_id', '=', bom.product_id.id), ('bom_id', '=', False)])
                if no_child_bom and bom.id not in no_child_bom:
                    other_bom = bom_obj.browse(cr, uid, no_child_bom)[0] #TODO zero before?
                    if not other_bom.product_id.calculate_price:
                        price += self._calc_price(cr, uid, other_bom) * other_bom.product_qty
                    else:
#                        price += other_bom.product_qty * other_bom.product_id.standard_price
                        price += other_bom.product_id.standard_price
                else:
#                    price += bom.product_qty * bom.product_id.standard_price
                    price += bom.product_id.standard_price
#                if no_child_bom:
#                    other_bom = bom_obj.browse(cr, uid, no_child_bom)[0]
#                    price += bom.product_qty * self._calc_price(cr, uid, other_bom)
#                else:
#                    price += bom.product_qty * bom.product_id.standard_price

            if bom.routing_id:
                for wline in bom.routing_id.workcenter_lines:
                    wc = wline.workcenter_id
                    cycle = wline.cycle_nbr
                    hour = (wc.time_start + wc.time_stop + cycle * wc.time_cycle) *  (wc.time_efficiency or 1.0)
                    price += wc.costs_cycle * cycle + wc.costs_hour * hour
                    price = self.pool.get('product.uom')._compute_price(cr,uid,bom.product_uom.id,price,bom.product_id.uom_id.id)
            if bom.bom_lines:
                self.write(cr, uid, [bom.product_id.id], {'standard_price' : price/bom.product_qty})
            if bom.product_uom.id != bom.product_id.uom_id.id:
                price = self.pool.get('product.uom')._compute_price(cr,uid,bom.product_uom.id,price,bom.product_id.uom_id.id)
            return price
product_product()

class product_bom(osv.osv):
    _inherit = 'mrp.bom'
            
    _columns = {
        'standard_price': fields.related('product_id','standard_price',type="float",relation="product.product",string="Standard Price",store=False)
    }

product_bom()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

