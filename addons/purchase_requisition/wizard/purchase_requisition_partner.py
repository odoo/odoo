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
from osv.orm import browse_record, browse_null
from tools.translate import _

class purchase_requisition_partner(osv.osv_memory):
    _name = "purchase.requisition.partner"
    _description = "Purchase Requisition Partner"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Supplier', required=True,domain=[('supplier', '=', True)]),
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        res = super(purchase_requisition_partner, self).view_init(cr, uid, fields_list, context=context)
        record_id = context and context.get('active_id', False) or False
        tender = self.pool.get('purchase.requisition').browse(cr, uid, record_id, context=context)
        if not tender.line_ids:
            raise osv.except_osv(_('Error!'), _('No Product in Tender'))
        return res

    def create_order(self, cr, uid, ids, context=None):
        active_ids = context and context.get('active_ids', [])
        data =  self.browse(cr, uid, ids, context=context)[0]
        self.pool.get('purchase.requisition').make_purchase_order(cr, uid, active_ids, data.partner_id.id, context=context)
        return {'type': 'ir.actions.act_window_close'}

purchase_requisition_partner()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
