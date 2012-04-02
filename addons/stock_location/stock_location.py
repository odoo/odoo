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

from osv import fields,osv

class stock_location_path(osv.osv):
    _name = "stock.location.path"
    _description = "Pushed Flows"
    _columns = {
        'name': fields.char('Operation', size=64),
        'company_id': fields.many2one('res.company', 'Company'),
        'product_id' : fields.many2one('product.product', 'Products', ondelete='cascade', select=1),
        'journal_id': fields.many2one('stock.journal','Journal'),
        'location_from_id' : fields.many2one('stock.location', 'Source Location', ondelete='cascade', select=1, required=True),
        'location_dest_id' : fields.many2one('stock.location', 'Destination Location', ondelete='cascade', select=1, required=True),
        'delay': fields.integer('Delay (days)', help="Number of days to do this transition"),
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Status",
            required=True,),
        'picking_type': fields.selection([('out','Sending Goods'),('in','Getting Goods'),('internal','Internal')], 'Shipping Type', required=True, select=True, help="Depending on the company, choose whatever you want to receive or send products"),
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
        'auto': 'auto',
        'delay': 1,
        'invoice_state': 'none',
        'picking_type': 'internal',
    }
stock_location_path()

class product_pulled_flow(osv.osv):
    _name = 'product.pulled.flow'
    _description = "Pulled Flows"
    _columns = {
        'name': fields.char('Name', size=64, required=True, help="This field will fill the packing Origin and the name of its moves"),
        'cancel_cascade': fields.boolean('Cancel Cascade', help="Allow you to cancel moves related to the product pull flow"),
        'location_id': fields.many2one('stock.location','Destination Location', required=True, help="Is the destination location that needs supplying"),
        'location_src_id': fields.many2one('stock.location','Source Location', help="Location used by Destination Location to supply"),
        'journal_id': fields.many2one('stock.journal','Journal'),
        'procure_method': fields.selection([('make_to_stock','Make to Stock'),('make_to_order','Make to Order')], 'Procure Method', required=True, help="'Make to Stock': When needed, take from the stock or wait until re-supplying. 'Make to Order': When needed, purchase or produce for the procurement request."),
        'type_proc': fields.selection([('produce','Produce'),('buy','Buy'),('move','Move')], 'Type of Procurement', required=True),
        'company_id': fields.many2one('res.company', 'Company', help="Is used to know to which company belong packings and moves"),
        'partner_address_id': fields.many2one('res.partner', 'Partner Address'),
        'picking_type': fields.selection([('out','Sending Goods'),('in','Getting Goods'),('internal','Internal')], 'Shipping Type', required=True, select=True, help="Depending on the company, choose whatever you want to receive or send products"),
        'product_id':fields.many2one('product.product','Product'),
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Status",
            required=True,),
    }
    _defaults = {
        'cancel_cascade': False,
        'procure_method': 'make_to_stock',
        'type_proc': 'move',
        'picking_type': 'out',
        'invoice_state': 'none',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'product.pulled.flow', context=c),
    }
product_pulled_flow()

class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'flow_pull_ids': fields.one2many('product.pulled.flow', 'product_id', 'Pulled Flows'),
        'path_ids': fields.one2many('stock.location.path', 'product_id',
            'Pushed Flow',
            help="These rules set the right path of the product in the "\
            "whole location tree.")
    }
product_product()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'cancel_cascade': fields.boolean('Cancel Cascade', help='If checked, when this move is cancelled, cancel the linked move too')
    }
    def action_cancel(self, cr, uid, ids, context=None):
        for m in self.browse(cr, uid, ids, context=context):
            if m.cancel_cascade and m.move_dest_id:
                self.action_cancel(cr, uid, [m.move_dest_id.id], context=context)
        res = super(stock_move,self).action_cancel(cr,uid,ids,context)
        return res
stock_move()

class stock_location(osv.osv):
    _inherit = 'stock.location'
    def chained_location_get(self, cr, uid, location, partner=None, product=None, context=None):
        if product:
            for path in product.path_ids:
                if path.location_from_id.id == location.id:
                    return path.location_dest_id, path.auto, path.delay, path.journal_id and path.journal_id.id or False, path.company_id and path.company_id.id or False, path.picking_type
        return super(stock_location, self).chained_location_get(cr, uid, location, partner, product, context)
stock_location()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
