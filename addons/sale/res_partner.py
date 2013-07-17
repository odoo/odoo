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
from openerp.tools.translate import _

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _sale_order_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,0), ids))
        # The current user may not have access rights for sale orders
        try:
            for partner in self.browse(cr, uid, ids, context):
                res[partner.id] = len(partner.sale_order_ids)
        except:
            pass
        return res

    def copy(self, cr, uid, record_id, default=None, context=None):
        if default is None:
            default = {}

        default.update({'sale_order_ids': []})

        super(res_partner, self).copy(cr, uid, record_id, default, context)

    _columns = {
        'sale_order_count': fields.function(_sale_order_count, string='# of Sales Order', type='integer'),
        'sale_order_ids': fields.one2many('sale.order','partner_id','Sales Order')
    }

