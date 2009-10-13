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
import datetime
import pooler

form='''<?xml version="1.0"?>
<form string="Choose">
    <field name="date_from"/>
    <field name="date_to"/>
    <field name="journal_ids" colspan="4"/>
    <field name="employee_ids" colspan="4"/>
</form>'''

class wizard_report(wizard.interface):
    def _date_from(*a):
        return datetime.datetime.today().strftime('%Y-%m-1')
    
    def _date_to(*a):
        return datetime.datetime.today().strftime('%Y-%m-%d')
    
    def _check(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        line_obj = pool.get('account.analytic.line')
        product_obj = pool.get('product.product')
        price_obj = pool.get('product.pricelist')
        ids = line_obj.search(cr, uid, [
                ('date', '>=', data['form']['date_from']),
                ('date', '<=', data['form']['date_to']),
                ('journal_id', 'in', data['form']['journal_ids'][0][2]),
                ('user_id', 'in', data['form']['employee_ids'][0][2]),
                ])
        if not ids:
            raise wizard.except_wizard(_('Data Insufficient!'), _('No Records Found for Report!'))
        
        return data['form']
    

    fields={
        'date_from':{
            'string':'From',
            'type':'date',
            'required':True,
            'default':_date_from,
        },
        'date_to':{
            'string':'To',
            'type':'date',
            'required':True,
            'default':_date_to,
        },
        'journal_ids':{
            'string':'Journal',
            'type':'many2many',
            'relation':'account.analytic.journal',
            'required':True,
        },
        'employee_ids':{
            'string':'Employee',
            'type':'many2many',
            'relation':'res.users',
            'required':True,
        },
    }

    states={
        'init':{
            'actions':[],
            'result':{'type':'form', 'arch':form, 'fields':fields, 'state':[('end', 'Cancel'), ('report', 'Print')]}
        },
        'report':{
            'actions':[_check],
            'result':{'type':'print', 'report':'account.analytic.profit', 'state':'end'}
        }
    }
wizard_report('account.analytic.profit')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

