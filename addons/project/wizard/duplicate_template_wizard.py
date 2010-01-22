# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from mx.DateTime import now

import wizard
import netsvc
import ir
import pooler
import time

from tools.translate import _

class project_duplicate_template(wizard.interface):

    def duplicate_template(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        project_obj = pool.get('project.project')
        res = project_obj.duplicate_template(cr, uid, data['ids'])        
        if res and len(res):
            res_id = res[0]        
            data_obj = pool.get('ir.model.data')                        
            form_view_id = data_obj._get_id(cr, uid, 'project', 'edit_project')
            form_view = data_obj.read(cr, uid, form_view_id, ['res_id']) 
            tree_view_id = data_obj._get_id(cr, uid, 'project', 'view_project_list')
            tree_view = data_obj.read(cr, uid, tree_view_id, ['res_id']) 
            search_view_id = data_obj._get_id(cr, uid, 'project', 'view_project_project_filter')
            search_view = data_obj.read(cr, uid, search_view_id, ['res_id'])                        
            return {            
                'name': _('Projects'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'project.project',
                'view_id': False,
                'res_id' : res_id,
                'views': [(form_view['res_id'],'form'),(tree_view['res_id'],'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view['res_id']
                }
        return {}
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'action', 'action': duplicate_template, 'state': 'order'}
        },
        'order': {
            'actions': [],
            'result': {'type': 'state', 'state': 'end'}
        }
    }
project_duplicate_template('project.duplicate.template')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
