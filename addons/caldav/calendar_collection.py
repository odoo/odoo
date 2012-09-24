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
from tools.translate import _
import caldav_node
import logging
_logger = logging.getLogger(__name__)

class calendar_collection(osv.osv):
    _inherit = 'document.directory' 
    _columns = {
        'calendar_collection' : fields.boolean('Calendar Collection'),
        'calendar_ids': fields.one2many('basic.calendar', 'collection_id', 'Calendars'),
    }
    _default = {
        'calendar_collection' : False,
    }
    
    def _get_root_calendar_directory(self, cr, uid, context=None):
        objid = self.pool.get('ir.model.data')
        try:
            mid = objid._get_id(cr, uid, 'document', 'dir_calendars')
            if not mid:
                return False
            root_id = objid.read(cr, uid, mid, ['res_id'])['res_id']
            root_cal_dir = self.browse(cr,uid, root_id, context=context) 
            return root_cal_dir.name
        except Exception:
            _logger.warning('Cannot set root directory for Calendars:', exc_info=True)
            return False
        return False

    def get_node_class(self, cr, uid, ids, dbro=None, dynamic=False, context=None):
        if dbro is None:
            dbro = self.browse(cr, uid, ids, context=context)

        if dbro.calendar_collection:
            if dynamic:
                return caldav_node.node_calendar_res_col
            else:
                return caldav_node.node_calendar_collection
        else:
            return super(calendar_collection, self).\
                    get_node_class(cr, uid, ids, dbro=dbro,dynamic=dynamic, 
                                    context=context)

    def get_description(self, cr, uid, ids, context=None):
        #TODO : return description of all calendars
        return False

    def get_schedule_inbox_URL(self, cr, uid, ids, context=None):
        calendar_obj = self.pool.get('basic.calendar')

        calendar_ids = calendar_obj.search(cr, uid, [
            ('user_id', '=', uid), ('collection_id', 'in', ids)
            ], limit=1, context=context)

        root_cal_dir = self._get_root_calendar_directory(cr, uid, context=context)
        if not calendar_ids:
            return root_cal_dir
        calendar_id = calendar_ids[0]
        calendar = calendar_obj.browse(cr, uid, calendar_id,
                context=context)
        return '%s/%s' %(root_cal_dir, calendar.name)

    def get_schedule_outbox_URL(self, cr, uid, ids, context=None):
        return self.get_schedule_inbox_URL(cr, uid, ids, context=context)
    
calendar_collection()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
