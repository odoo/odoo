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

from osv import fields, osv
from tools.translate import _
import netsvc
import pooler
import time
import tools
import wizard
import base64

class calendar_event_import(osv.osv_memory):
    """
    Import Calendar Event.
    """
    cnt = 0

    def process_imp_ics(self, cr, uid, ids, context=None):
        """
        Process Import ics File.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of calendar event import’s IDs
        @return: dictionary of calendar evet import  window with Import successful msg.
        """
        if context is None:
            context = {}
        else:
            context = context.copy()
        context['uid'] = uid

        for data in self.read(cr, uid, ids, context=context):
            model = data.get('model', 'basic.calendar')
            model_obj = self.pool.get(model)
            context.update({'model': model})
            data_obj = self.pool.get('ir.model.data')
            id2 = data_obj._get_id(cr, uid, 'caldav', 'view_calendar_event_import_display')
            if id2:
                 id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            vals = None
            try:
                vals = model_obj.import_cal(cr, uid, base64.decodestring(data['file_path']), context['active_id'], context)
            except:
                raise osv.except_osv(_('Warning!'),_('Invalid format of the ics, file cannot be imported.'))
            global cnt
            if vals:
                cnt = len(vals)
            value = {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'calendar.event.import',
                'views': [(id2,'form'),(False,'tree'),(False,'calendar'),(False,'graph')],
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
            return value

    _name = "calendar.event.import"
    _description = "Event Import"

    _columns = {
                  'file_path': fields.binary('Select ICS File', filters='*.ics', required=True),
                  'msg': fields.text('', readonly=True),
               }

    def _get_msg(self, cr, uid, context):
        return _('Import Sucessful')
        
    _defaults = {
               'msg': _get_msg,
               }

calendar_event_import()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
