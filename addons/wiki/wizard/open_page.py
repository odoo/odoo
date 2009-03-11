# -*- encoding: utf-8 -*-
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

class wiz_timesheet_open(wizard.interface):
    
    def _open_wiki_page(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        menu_id = data['id']
        group_ids = pool.get('wiki.groups.link').search(cr, uid, [('action_id','=',menu_id)])
        if not group_ids:
            raise wizard.except_wizard(_('Open Page'), _('No action found'))
        group = pool.get('wiki.groups.link').browse(cr, uid, group_ids[0])
        
        value = {
            'context': "{'group_id':%d, 'section':%s}" % (group.group_id.id, group.group_id.section),
            'domain': "[('group_id','child_of',[%s])]" % (group.group_id.id),
            'name': 'Wiki Page',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'wiki.wiki',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        if group.group_id.home:
            value['res_id'] = group.group_id.home.id
        else:
            value['view_type'] = 'form'
            value['view_mode'] = 'tree,form'
            
        return value

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_open_wiki_page, 'state':'end'}
        }
    }
wiz_timesheet_open('wiki.wiki.page.open')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

