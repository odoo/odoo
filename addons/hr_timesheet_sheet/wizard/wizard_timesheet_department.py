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

class wiz_timesheet_open(wizard.interface):
    def _open_timesheet(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        dep_ids = pool.get('hr.department').search(cr, uid, [('manager_id','=',uid)])
        user_ids = {}
        for dep in pool.get('hr.department').browse(cr, uid, dep_ids, context):
            for user in dep.member_ids:
                user_ids[user.id] = 1
        value = {
            'domain': "[('user_id', 'in', "+str(user_ids.keys())+")]",
            'name': 'Timesheets',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr_timesheet_sheet.sheet',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        return value

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_open_timesheet, 'state':'end'}
        }
    }
wiz_timesheet_open('hr_timesheet_sheet.department.open')

class wiz_timesheet_confirm_open(wizard.interface):
    def _open_timesheet(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        dep_ids = pool.get('hr.department').search(cr, uid, [('manager_id','=',uid)])
        user_ids = {}
        for dep in pool.get('hr.department').browse(cr, uid, dep_ids, context):
            for user in dep.member_ids:
                user_ids[user.id] = 1
        value = {
            'domain': "[('user_id', 'in', "+str(user_ids.keys())+"),('state','=','draft')]",
            'name': 'Timesheets',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr_timesheet_sheet.sheet',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        return value

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_open_timesheet, 'state':'end'}
        }
    }
wiz_timesheet_confirm_open('hr_timesheet_sheet.department.confirm.open')


class wiz_timesheet_validate_open(wizard.interface):
    def _open_timesheet(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        dep_ids = pool.get('hr.department').search(cr, uid, [('manager_id','=',uid)])
        user_ids = {}
        for dep in pool.get('hr.department').browse(cr, uid, dep_ids, context):
            for user in dep.member_ids:
                user_ids[user.id] = 1
        value = {
            'domain': "[('user_id', 'in', "+str(user_ids.keys())+"),('state','=','confirm')]",
            'name': 'Timesheets',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr_timesheet_sheet.sheet',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        return value

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_open_timesheet, 'state':'end'}
        }
    }
wiz_timesheet_validate_open('hr_timesheet_sheet.department.validate.open')



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

