# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: project.py 1011 2005-07-26 08:11:45Z nicoe $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
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

