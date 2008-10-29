# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
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
import time
import netsvc
import pooler
import tools


class one2many_mod_task(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if not context:
            context = {}
        if not values:
                values = {}
        res = {}
        for id in ids:
            res[id] = []
        for id in ids:
            query = "select project_id from event_event where id = %i" %id
            cr.execute(query)
            project_ids = [ x[0] for x in cr.fetchall()]
            ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id,'in',project_ids),('state','<>','done')], limit=self._limit)
            for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
                res[id].append( r['id'] )
        return res

class event(osv.osv):
    _inherit = 'event.event'

    def write(self, cr, uid, ids,vals, *args, **kwargs):
        if 'date_begin' in vals and vals['date_begin']:
            for eve in self.browse(cr, uid, ids):
                    self.pool.get('project.project').write(cr, uid, [eve.project_id.id], {'date_end':eve.date_begin})

        return super(event,self).write(cr, uid, ids,vals, *args, **kwargs)

    _columns = {
        'project_id': fields.many2one('project.project', 'Project', readonly=True),
        'task_ids': one2many_mod_task('project.task', 'project_id', "Project tasks", readonly=True, domain="[('state','&lt;&gt;', 'done')]"),
    }
event()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

