# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP S.A. (<http://www.openerp.com>).
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

def _compute_price(self, cr, uid, data, context):
    bom_obj = self.pool.get('mrp.bom')

    for bom in bom_obj.browse(cr, uid, data['ids'], context=context):
        bom.product_id.compute_price(cr, uid, bom.product_id.id)
    return {}


class wizard_price(osv.osv):
    _name = "wizard.price"
    _description = "Compute price wizard"
    states = {
        'init' : {
            'actions' : [],
            'result' : {
                'type' : 'action',
                'action' : _compute_price,
                'state' : 'end'
            }
        },
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

