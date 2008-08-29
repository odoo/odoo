# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: sign_in_out.py 2871 2006-04-25 14:08:22Z ged $
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

