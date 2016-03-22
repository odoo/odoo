# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class product_removal_strategy(osv.osv):
    _name = 'product.removal'
    _description = 'Removal Strategy'

    _columns = {
        'name': fields.char('Name', required=True),
        'method': fields.char("Method", required=True, help="FIFO, LIFO..."),
    }


class product_putaway_strategy(osv.osv):
    _name = 'product.putaway'
    _description = 'Put Away Strategy'

    def _get_putaway_options(self, cr, uid, context=None):
        return [('fixed', 'Fixed Location')]

    _columns = {
        'name': fields.char('Name', required=True),
        'method': fields.selection(_get_putaway_options, "Method", required=True),
        'fixed_location_ids': fields.one2many('stock.fixed.putaway.strat', 'putaway_id', 'Fixed Locations Per Product Category', help="When the method is fixed, this location will be used to store the products", copy=True),
    }

    _defaults = {
        'method': 'fixed',
    }

    def putaway_apply(self, cr, uid, ids, product, context=None):
        putaway_strat = self.browse(cr, uid, ids[0], context=context)
        if putaway_strat.method == 'fixed':
            for strat in putaway_strat.fixed_location_ids:
                categ = product.categ_id
                while categ:
                    if strat.category_id.id == categ.id:
                        return strat.fixed_location_id.id
                    categ = categ.parent_id


class fixed_putaway_strat(osv.osv):
    _name = 'stock.fixed.putaway.strat'
    _order = 'sequence'
    _columns = {
        'putaway_id': fields.many2one('product.putaway', 'Put Away Method', required=True),
        'category_id': fields.many2one('product.category', 'Product Category', required=True),
        'fixed_location_id': fields.many2one('stock.location', 'Location', required=True),
        'sequence': fields.integer('Priority', help="Give to the more specialized category, a higher priority to have them in top of the list."),
    }