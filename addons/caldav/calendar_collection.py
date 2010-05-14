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
            root_cal_dir = self.browse(cr, uid, root_id, context=context) 
            return root_cal_dir.name
        except Exception, e:
            import netsvc
            logger = netsvc.Logger()
            logger.notifyChannel("document", netsvc.LOG_WARNING, 'Cannot set root directory for Calendars:'+ str(e))
            return False
        return False

    def _locate_child(self, cr, uid, root_id, uri,nparent, ncontext):
        """ try to locate the node in uri,
            Return a tuple (node_dir, remaining_path)
        """
        return (caldav_node.node_database(context=ncontext), uri)

    def get_description(self, cr, uid, ids, context=None):
        #TODO : return description of all calendars
        if not context:
            context = {}
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
