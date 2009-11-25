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
from tools.translate import _
import pooler

_voucher_form = '''<?xml version="1.0"?>
<form string="Open Vouchers">
    <field name="type"/>
    <field name="state"/>
    <field name="period_ids" colspan="4"/>
</form>'''

_types = {
    'pay_voucher':'Cash Payment Voucher',
    'bank_pay_voucher':'Bank Payment Voucher',
    'rec_voucher':'Cash Receipt Voucher',
    'bank_rec_voucher':'Bank Receipt Voucher',
    'cont_voucher':'Contra Voucher',
    'journal_sale_vou':'Journal Sale Voucher',
    'journal_pur_voucher':'Journal Purchase Voucher'
}
_states = {
    'draft':'Draft',
    'proforma':'Pro-forma',
    'posted':'Posted',
    'cancel':'Cancel'  
}

_voucher_fields = {
    'type': {'string':'Voucher Type', 'type':'selection', 'selection':[
            ('pay_voucher','Cash Payment Voucher'),
            ('bank_pay_voucher','Bank Payment Voucher'),
            ('rec_voucher','Cash Receipt Voucher'),
            ('bank_rec_voucher','Bank Receipt Voucher'),
            ('cont_voucher','Contra Voucher'),
            ('journal_sale_vou','Journal Sale Voucher'),
            ('journal_pur_voucher','Journal Purchase Voucher')], 'required':True},
    'state': {'string':'State', 'type':'selection', 'selection':[
                    ('draft','Draft'),
                    ('proforma','Pro-forma'),
                    ('posted','Posted'),
                    ('cancel','Cancel')], 'required':True},
    'period_ids': {'string':'Periods', 'type':'many2many', 'relation':'account.period'},
}

def _action_open_window(self, cr, uid, data, context):
    form = data['form']
    periods = []
    
    if not form['period_ids'][0][2]:
        pool = pooler.get_pool(cr.dbname)
        period = pool.get('account.period')
        year = pool.get('account.fiscalyear')
        
        year = year.find(cr, uid)
        periods = period.search(cr, uid, [('fiscalyear_id','=',year)])
    else:
        periods = form['period_ids'][0][2]
        
    return {
        'domain': "[('type','=','%s'), ('state','=','%s'), ('period_id','in',%s)]" % (form['type'], form['state'], periods),
        'name': "%s - %s" % (_types[form['type']], _states[form['state']]),
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.voucher',
        'view_id': False,
        'context': "{'type':'%s', 'state':'%s', 'period_id':%s}" % (form['type'], form['state'], periods),
        'type': 'ir.actions.act_window'
    }

class OpenVoucherEntries(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_voucher_form, 'fields':_voucher_fields, 'state':[('end','Cancel'),('open','Open Voucher Entries')]}
        },
        'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
OpenVoucherEntries('account.voucher.open')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
