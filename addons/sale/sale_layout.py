# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields


class SaleLayoutCategory(osv.Model):
    _name = 'sale.layout_category'
    _order = 'sequence, id'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', required=True),
        'subtotal': fields.boolean('Add subtotal'),
        'pagebreak': fields.boolean('Add pagebreak')
    }

    _defaults = {
        'subtotal': True,
        'pagebreak': False,
        'sequence': 10
    }
