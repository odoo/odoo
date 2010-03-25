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

class calendar_event_export(osv.osv_memory):
    """
    Export Calendar Event.
    """
    def _process_export_ics(self, cr, uid, context):
        """
        Get Default value for file_path field.
        """
        model = context.get('model', 'basic.calendar')
        model_obj = self.pool.get(model)
        calendar = model_obj.export_cal(cr, uid, context['active_ids'], context)
        #TODO: check why returns wrong value
        return base64.encodestring(calendar)

    def _process_export_ics_name(self, cr, uid, context):
        """
        Get Default value for Name field.
        """
        model = context.get('model', 'basic.calendar')
        model_obj = self.pool.get(model)
        calendar = model_obj.export_cal(cr, uid, context['active_ids'], context)
        return  'OpenERP %s.ics' % (model_obj._description)

    _name = "calendar.event.export"
    _description = "Event Export"

    _columns = {
              'file_path':fields.binary('Save ICS file', filters='*.ics', required=True),
              'name':fields.char('File name', size=34, required=True, help='Save in .ics format')
               }

    _defaults = {
               'name': _process_export_ics_name,
               'file_path': _process_export_ics
               }

calendar_event_export()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
