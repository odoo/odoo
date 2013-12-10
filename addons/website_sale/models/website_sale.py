# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C)-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version of the
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

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields

class sale_order(osv.Model):
    _inherit = "sale.order"

    _columns = {
        'website_session_id': fields.char('Session UUID4'),
    }

    def get_total_quantity(self, cr, uid, ids, context=None):
        order = self.browse(cr, uid, ids[0], context=context)
        return int(sum(l.product_uom_qty for l in (order.order_line or [])))


class sale_order_line(osv.Model):
    _inherit = "sale.order.line"

    def _recalculate_product_values(self, cr, uid, ids, product_id=0, context=None):
        if context is None:
            context = {}
        user_obj = self.pool.get('res.users')
        product_id = product_id or ids and self.browse(cr, uid, ids[0], context=context).product_id.id

        return self.product_id_change(
            cr, SUPERUSER_ID, ids,
            pricelist=context.pop('pricelist'),
            product=product_id,
            partner_id=user_obj.browse(cr, SUPERUSER_ID, uid).partner_id.id,
            context=context
        )['value']
