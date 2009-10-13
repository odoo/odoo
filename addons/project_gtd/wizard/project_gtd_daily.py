# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import wizard
import netsvc
import time
import pooler
from osv import osv
from tools.translate import _

class wiz_timebox_open(wizard.interface):
    def _open_timebox(self, cr, uid, data, context):
        tbtype = 'daily'
        pool = pooler.get_pool(cr.dbname)
        ids = pool.get('project.gtd.timebox').search(cr, uid, [('user_id','=',uid),('type','=',tbtype)])
        if not len(ids):
            raise wizard.except_wizard(_('Error !'), _('No timebox of the type "%s" defined !') % (tbtype,))
        view_type = 'form,tree'
        if len(ids) >= 1:
            domain = "[('id','in',["+','.join(map(str,ids))+"])]"
        else:
            domain = "[('user_id', '=', uid)]"
        value = {
            'domain': domain,
            'name': 'My Daily Timebox',
            'view_type': 'form',
            'view_mode': view_type,
            'res_model': 'project.gtd.timebox',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        if len(ids) == 1:
            value['res_id'] = ids[0]
            value['context'] = {'record_id':ids[0]}
        return value

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_open_timebox, 'state':'end'}
        }
    }
wiz_timebox_open('project.gtd.timebox.daily')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

