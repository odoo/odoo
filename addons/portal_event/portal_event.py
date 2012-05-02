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

import time
from osv import fields, osv
from tools.translate import _

class event_event(osv.osv):
    _inherit = 'event.event'

    def make_quotation(self, cr, uid, ids, context=None):
        event_pool = self.pool.get('event.event')
        register_pool = self.pool.get('event.registration')
        sale_order_line_pool = self.pool.get('sale.order.line')
        sale_order = self.pool.get('sale.order')
        partner_pool = self.pool.get('res.partner')
        prod_pricelist_obj = self.pool.get('product.pricelist')
        res_users_obj = self.pool.get('res.users')
        user = res_users_obj.browse(cr, uid, uid, context=context)
        partner_ids = partner_pool.search(cr, uid, [('name', '=', user.name), ('email', '=', user.user_email)])
        if partner_ids:
            res_users_obj.write(cr, uid, user.id, {'partner_id': partner_ids[0]})        
        if not partner_ids:
              raise osv.except_osv(_('Error !'),
                                    _('There is no Partner defined ' \
                                            'for this event:'))
        res = super(event_event,self).make_quotation(cr, uid, ids, context)              

        return res
