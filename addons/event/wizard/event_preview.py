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

from osv import osv, fields

    
class event_preview(osv.osv_memory):
    _name = 'event.preview'
    _inherit= 'event.event'
    _columns = {
     'qty': fields.integer('Quantity'),
     'sale_end_date': fields.datetime('SalesEnd'),
    }
    def default_get(self, cr, uid, fields, context=None):
        event_pool = self.pool.get('event.event')
        data_obj = self.pool.get('ir.model.data')
        res_id = data_obj._get_id(cr, uid, 'event', 'view_event_preview')
        if res_id:
            event_preview_id = data_obj.browse(cr, uid, res_id, context=context).res_id

        record_ids = context and context.get('active_ids', []) or []
        res = {}
        for event in event_pool.browse(cr, uid, record_ids, context=context):
            if 'name' in fields:
                res.update({'name': event.name})
            if 'date_begin' in fields:
                res.update({'date_begin': event.date_begin or False})
            if 'address_id' in fields:
                res.update({'address_id': event.address_id and event.address_id.id or False})
            if 'date_end' in fields:
                res.update({'date_end': event.date_end})
            if 'note' in fields:
                res.update({'note': event.note})
        return res
    
event_preview()   

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: