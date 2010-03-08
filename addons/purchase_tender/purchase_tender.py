# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from osv import fields,osv
from osv import orm
import netsvc
import time

class purchase_tender(osv.osv):
    _name = "purchase.tender"
    _description="Purchase Tender"
    _columns = {
        'name': fields.char('Tender Reference', size=32,required=True),
        'date_start': fields.datetime('Date Start'),
        'date_end': fields.datetime('Date End'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'description': fields.text('Description'),
        'purchase_ids' : fields.one2many('purchase.order','tender_id','Purchase Orders'),
        'state': fields.selection([('draft','Draft'),('open','Open'),('close','Close')], 'State', required=True)
    }
    _defaults = {
        'date_start': lambda *args: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': lambda *args: 'open',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'purchase.order.tender'),
    }
purchase_tender()

class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _description = "purchase order"
    _columns = {
        'tender_id' : fields.many2one('purchase.tender','Purchase Tender')
    }
    def wkf_confirm_order(self, cr, uid, ids, context={}):
        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context)
        for po in self.browse(cr, uid, ids, context):
            if po.tender_id:
                for order in po.tender_id.purchase_ids:
                    if order.id<>po.id:
                        wf_service = netsvc.LocalService("workflow")
                        wf_service.trg_validate(uid, 'purchase.order', order.id, 'purchase_cancel', cr)
                    self.pool.get('purchase.tender').write(cr, uid, [po.tender_id.id], {'state':'close'})
        return res
purchase_order()
