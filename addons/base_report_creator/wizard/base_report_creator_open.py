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




class report_creator_open(wizard.interface):
    def _open_report(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        rep = pool.get('base_report_creator.report').browse(cr, uid, data['id'], context)
        view_mode = rep.view_type1
        if rep.view_type2:
            view_mode += ','+rep.view_type2
        if rep.view_type3:
            view_mode += ','+rep.view_type3
        value = {
            'name': rep.name,
            'view_type': 'form',
            'view_mode': view_mode,
            'res_model': 'base_report_creator.report',
            'context': {'report_id': data['id']},
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        return value

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type':'action', 'action':_open_report, 'state':'end'}
        }
    }
report_creator_open('base_report_creator.report.open')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

