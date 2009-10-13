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

_time_unit_form = '''<?xml version="1.0"?>
<form string="Select time unit">
    <field name="time_unit"/>
    <newline/>
    <field name="measure_unit"/>
</form>'''

_time_unit_fields = {
    'time_unit': {'string':'Type of period', 'type':'selection', 'selection':[('day', 'Day by day'),('week', 'Per week'),('month', 'Per month')], 'required':True},
    'measure_unit': {'string':'Amount measuring unit', 'type':'selection', 'selection':[('hours', 'Amount in hours'),('cycles', 'Amount in cycles')], 'required':True},
}

class wizard_mrp_workcenter(wizard.interface):
    states = {
        'init': {
            'actions': [], 
            'result': {'type':'form', 'arch':_time_unit_form, 'fields':_time_unit_fields, 'state':[('end','Cancel'),('report','Print') ]},
        },
        'report': {
            'actions': [],
            'result': {'type':'print', 'report':'mrp.workcenter.load', 'state':'end'},
        },
    }

wizard_mrp_workcenter('mrp.workcenter.load')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

