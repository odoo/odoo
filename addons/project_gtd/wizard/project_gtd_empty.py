# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: sign_in_out.py 2871 2006-04-25 14:08:22Z fp $
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


import wizard
import netsvc
import time
import pooler
from osv import osv

class wiz_timebox_empty(wizard.interface):
    def _empty(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        ids = pool.get('project.gtd.timebox').search(cr, uid, [('parent_id','=',data['id'])])
        if not len(ids):
            raise wizard.except_wizard('Error !', 'No timebox child of this one !')
        tids = pool.get('project.task').search(cr, uid, [('timebox_id','=',data['id'])])
        close = []
        up = []
        for task in pool.get('project.task').browse(cr, uid, tids, context):
            if (task.state in ('cancel','done')) or (task.user_id.id<>uid):
                close.append(task.id)
            else:
                up.append(task.id)
        if up:
            print 'UP', up
            pool.get('project.task').write(cr, uid, up, {'timebox_id':ids[0]})
        if close:
            print 'CLOSE', close
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

