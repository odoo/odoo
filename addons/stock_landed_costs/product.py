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

from openerp.osv import fields, osv

SPLIT_METHOD = [
    ('equal', 'Equal'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost Price'),
    ('by_weight', 'By Weight'),
    ('by_volume', 'By Volume'),
]

class product_template(osv.osv):
    _inherit = "product.template"

    _columns = {
        'landed_cost_ok': fields.boolean('Can constitute a landed cost'),
        'split_method': fields.selection(SPLIT_METHOD, 'Split Method'),
    }

    _defaults = {
        'landed_cost_ok': False,
        'split_method': 'equal',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
