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

from openerp.osv import fields,osv

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
        'company_id': fields.many2one('res.company', 'Company', help="Is used to know to which company the pickings and moves belong."),
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


class product_putaway_strategy(osv.osv):
    
    def _calc_product_ids(self, cr, uid, ids, field, arg, context=None):
        '''
        This function should check on which products (including if the products are in a product category) this putaway strategy is used
        '''
        pass
    
    _name = 'product.putaway'
    _description = 'Put Away Strategy'
    _columns = {
        'product_ids':fields.function(_calc_product_ids, "Products"), 
        'product_categ_id':fields.many2one('product.category', 'Product Category', required=True),
        'location_id': fields.many2one('stock.location','Parent Location', help="Parent Destination Location from which a child bin location needs to be chosen", required=True), #domain=[('type', '=', 'parent')], 
        'method': fields.selection([('empty', 'Empty'), ('fixed', 'Fixed Location')], "Method", required = True),
                }


class product_removal_strategy(osv.osv):

    def _calc_product_ids(self, cr, uid, ids, field, arg, context=None):
        '''
        This function should check on which products (including if the products are in a product category) this removal strategy is used
        '''
        pass
    
    _name = 'product.removal'
    _description = 'Removal Strategy'
    _columns = {
        'product_ids':fields.function(_calc_product_ids, "Products"),
        'product_categ_id':fields.many2one('product.category', 'Product Category', required=True),
        'location_id': fields.many2one('stock.location', 'Parent Location', help="Parent Source Location from which a child bin location needs to be chosen", required=True), #, domain=[('type', '=', 'parent')]
        'method': fields.selection([('fifo', 'FIFO'), ('lifo', 'LIFO')], "Method", required=True), 
        }




class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'flow_pull_ids': fields.one2many('product.pulled.flow', 'product_id', 'Pulled Flows'),
        'path_ids': fields.one2many('stock.location.path', 'product_id',
            'Pushed Flow',
            help="These rules set the right path of the product in the "\
            "whole location tree.")
    }


class product_category(osv.osv):
    _inherit = 'product.category'
    _columns = {
        #'route_ids': fields.many2many('stock.route', 'product_catg_id', 'route_id', 'Routes'), 
        'removal_strategy_ids': fields.one2many('product.removal', 'product_categ_id', 'Removal Strategies'),
        'putaway_strategy_ids': fields.one2many('product.putaway', 'product_categ_id', 'Put Away Strategies'),
    }




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

    def splitforputaway (self, cr, uid, ids, context=None):
        '''
        Splits this move in order to do the put away
        
        Happens at move getting done
        '''
        putaway_obj = self.pool.get("product.putaway")
        location_obj = self.pool.get("stock.location")
        quant_obj = self.pool.get("stock.quant")
        for move in self.browse(cr, uid, ids, context=context):
            putaways = location_obj.get_putaway_strategy(cr, uid, move.location_dest_id.id, context=context)#putaway_obj.search(cr, uid, [('product_categ_id','=', move.product_id.categ_id.id), ('location_id', '=', move.location_dest_id.id)], context=context)
            if putaways: 
                #Search for locations for PutAway
                locs = location_obj.search(cr, uid, [('id', 'child_of', move.location_dest_id.id), ('id', '!=', move.location_dest_id.id), ('quant_ids', '=', False), 
                                                     ('destination_move_ids', '=', False)], context=context)
                if locs:
                    quants = quant_obj.search(cr, uid, [('history_ids', 'in', move.id)])
                    quant_obj.write(cr, uid, quants, {'location_id': locs[0]}, context=context)
        return True



    def _prepare_chained_picking(self, cr, uid, picking_name, picking, picking_type, moves_todo, context=None):
        res = super(stock_move, self)._prepare_chained_picking(cr, uid, picking_name, picking, picking_type, moves_todo, context=context)
        res.update({'invoice_state': moves_todo[0][1][6] or 'none'})
        return res

class stock_location(osv.osv):
    _inherit = 'stock.location'
    _columns = {
        'removal_strategy_ids': fields.one2many('product.removal', 'location_id', 'Removal Strategies'),
        'putaway_strategy_ids': fields.one2many('product.putaway', 'location_id', 'Put Away Strategies'),
        }
    
    
    def search_putaways(self, cr, uid, id, product_categ_id, context=None):
        return self.pool.get('product.putaway').search(cr, uid, [('location_id','=',id), ('product_categ_id','=', product_categ_id)], context=context)
    

    def get_putaway_strategy(self, cr, uid, id, product_id, context=None):
        product = self.pool.get("product.product").browse(cr, uid, product_id, context=context)
        strats = self.search_putaways(cr, uid, id, product.categ_id.id, context=context)
        location = self.browse(cr, uid, id, context=context)
        categ = product.categ_id
        while not strats and categ.parent_id:
            while not strats and location.location_id:
                location = location.location_id
                strats = self.search_putaways(cr, uid, location.id, categ.id, context=context)
            categ = categ.parent_id
        return strats and strats[0] or False

    def search_removals(self, cr, uid, id, product_categ_id, context=None):
        return self.pool.get('product.removal').search(cr, uid, [('location_id','=',id), ('product_categ_id','=', product_categ_id)], context=context)
    

    def get_removal_strategy(self, cr, uid, id, product_id, context=None):
        #TODO improve code
        product = self.pool.get("product.product").browse(cr, uid, product_id, context=context)
        strats = self.search_removals(cr, uid, id, product.categ_id.id, context=context)
        location = self.browse(cr, uid, id, context=context)
        categ = product.categ_id
        while not strats and categ.parent_id:
            while not strats and location.location_id:
                location = location.location_id
                strats = self.search_removals(cr, uid, location.id, categ.id, context=context)
            categ = categ.parent_id
        return strats and strats[0] or super(stock_location, self).get_removal_strategy(cr, uid, id, product_id, context=context)

        


        return super(stock_location, self).get_removal_strategy(cr, uid, id, product_id, context=context)

    
    def chained_location_get(self, cr, uid, location, partner=None, product=None, context=None):
        if product:
            for path in product.path_ids:
                if path.location_from_id.id == location.id:
                    return path.location_dest_id, path.auto, path.delay, path.journal_id and path.journal_id.id or False, path.company_id and path.company_id.id or False, path.picking_type, path.invoice_state
        return super(stock_location, self).chained_location_get(cr, uid, location, partner, product, context)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
