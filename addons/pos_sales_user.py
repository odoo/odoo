# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

from osv import fields
from osv import osv
import time
import ir
from mx import DateTime
import datetime
import pooler
from tools import config
import wizard
import netsvc


sale_forecast_res_form= """<?xml version="1.0"?>
<form string="Sale by User">
     <field name="date_start" />
     <field name="date_end" />
     <field name="user_id" />

</form>
"""

sale_forecast_res_field= {
    'date_start': {'string':'Start Date','type':'date','required': True,'default': lambda *a: time.strftime('%Y-%m-%d')},
    'date_end': {'string':'End Date','type':'date','required': True,'default': lambda *a: time.strftime('%Y-%m-%d')},
    'user_id': {'string': 'Salesman', 'type': 'many2many', 'relation': 'res.users', 'required': True},

}


class wizard_pos_sales_user(wizard.interface):

    states = {
        'init' : {
            'actions' : [],
            'result' : {'type' : 'form',
                    'arch' : sale_forecast_res_form,
                    'fields' : sale_forecast_res_field,
                    'state' : [('end', 'Cancel','gtk-cancel'),('print_report', 'Print Report','gtk-print') ]}
        },
        'print_report' : {
            'actions' : [],
            'result' : {'type' : 'print',
                   'report':'pos.sales.user',
                    'state' : 'end'}
        },
    }
wizard_pos_sales_user('pos.sales.user')