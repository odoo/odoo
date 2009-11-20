# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import netsvc

class project_task(osv.osv):
    _name = "project.task"
    _inherit = "project.task"
    _columns = {
        'procurement_id': fields.many2one('mrp.procurement', 'Procurement', ondelete='set null')
    }
    def do_close(self, cr, uid, ids, *args):
        res = super(project_task, self).do_close(cr, uid, ids, *args)
        tasks = self.browse(cr, uid, ids)
        for task in tasks:
            if task.procurement_id:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'mrp.procurement', task.procurement_id.id, 'subflow.done', cr)
        return res

    def do_cancel(self, cr, uid, ids, *args):
        res = super(project_task, self).do_cancel(cr, uid, ids, *args)
        tasks = self.browse(cr, uid, ids)
        for task in tasks:
            if task.procurement_id:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'mrp.procurement', task.procurement_id.id, 'subflow.cancel', cr)
        return True
project_task()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

