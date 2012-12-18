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

class product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'auto_pick': fields.boolean('Auto Picking', help="Auto picking for raw materials of production orders.")
    }
    _defaults = {
        'auto_pick': True
    }
product()

class mrp_production(osv.osv):
    _inherit = "mrp.production"
    def _get_auto_picking(self, cr, uid, production):
        return production.product_id.auto_pick
mrp_production()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

