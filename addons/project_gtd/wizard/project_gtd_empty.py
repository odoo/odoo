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


import wizard
import netsvc
import time
import pooler
from osv import osv
from tools.translate import _

class wiz_timebox_empty(wizard.interface):
    def _empty(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        ids = pool.get('project.gtd.timebox').search(cr, uid, [])
        if not len(ids):
            raise wizard.except_wizard(_('Error !'), _('No timebox child of this one !'))
        tids = pool.get('project.task').search(cr, uid, [('timebox_id','=',data['id'])])
        close = []
        up = []
        for task in pool.get('project.task').browse(cr, uid, tids, context):
            if (task.state in ('cancel','done')) or (task.user_id.id<>uid):
                close.append(task.id)
            else:
                up.append(task.id)
        if up:
            pool.get('project.task').write(cr, uid, up, {'timebox_id':ids[0]})
        if close:
            pool.get('project.task').write(cr, uid, close, {'timebox_id':False})
        return {}

    states = {
        'init' : {
            'actions' : [_empty],
            'result' : {'type':'state', 'state':'end'}
        }
    }
wiz_timebox_empty('project.gtd.timebox.empty')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

