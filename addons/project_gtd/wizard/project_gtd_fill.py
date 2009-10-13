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
import pooler
from osv import osv

_gtd_field = {
    'task_ids': {'relation':'project.task', 'type':'many2many', 'string':'Tasks selection'},
    'timebox_to_id': {'relation':'project.gtd.timebox', 'type':'many2one', 'string':'Set to Timebox'},
    'timebox_id': {'relation':'project.gtd.timebox', 'type':'many2one', 'string':'Get from Timebox'}
}

_gtd_arch = """
    <form string="Timebox tasks selection" width="780">
        <field name="timebox_id" required="1"/>
        <field name="timebox_to_id" required="1"/>
        <field name="task_ids" nolabel="1" colspan="4" height="450" domain="[('timebox_id','=',timebox_id),('state','=','open')]"/>
    </form>
"""

class wiz_timebox_fill(wizard.interface):
    def _fill(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        ids = pool.get('project.gtd.timebox').search(cr, uid, [('parent_id','=',data['id']),('user_id','=',uid)], context=context)
        return {
            'timebox_id': ids and ids[0] or False,
            'timebox_to_id': data['id']
        }

    def _process(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        ids = data['form']['task_ids']
        pool.get('project.task').write(cr, uid, ids[0][2], {'timebox_id':data['form']['timebox_to_id']})
        return {}

    states = {
        'init' : {
            'actions' : [_fill],
            'result' : {
                'type':'form',
                'arch':_gtd_arch,
                'fields':_gtd_field,
                'state':[
                    ('end','Cancel'),
                    ('process','Add to Timebox')
                ]
            }
        },
        'process' : {
            'actions' : [_process],
            'result' : {'type':'state', 'state':'end'}
        }
    }
wiz_timebox_fill('project.gtd.timebox.fill')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

