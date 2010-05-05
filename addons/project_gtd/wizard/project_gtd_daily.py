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

class project_timebox_open(osv.osv_memory):

    _name = 'project.timebox.open'
    _description = 'Project Timebox Open'

    def open_tb(self, cr, uid, data, context=None):
        ids = self.pool.get('project.gtd.timebox').search(cr, uid, [])
        if not len(ids):
            raise osv.except_osv(_('Error !'), _('No timebox of the type defined !'))
        if len(ids) >= 1:
            domain = "[('id','in',["+','.join(map(str, ids))+"])]"
        value = {
            'domain': domain,
            'name': 'My Daily Timebox',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'project.gtd.timebox',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        if len(ids) == 1:
            value['res_id'] = ids[0]
            value['context'] = {'record_id':ids[0]}
        return value

project_timebox_open()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: