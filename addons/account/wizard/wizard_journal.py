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
from osv import osv
import pooler
from tools.translate import _

_journal_form = '''<?xml version="1.0"?>
<form string="Standard entries">
    <field name="journal_id"/>
    <newline/>
    <field name="period_id"/>
</form>'''

def _period_get(self, cr, uid, datas, ctx={}):
    try:
        pool = pooler.get_pool(cr.dbname)
        ids = pool.get('account.period').find(cr, uid, context=ctx)
        return {'period_id': ids[0]}
    except:
        return {}

_journal_fields = {
    'journal_id': {'string':'Journal', 'type':'many2one', 'relation':'account.journal', 'required':True},
    'period_id': {
        'string':'Period', 
        'type':'many2one', 
        'relation':'account.period', 
        'required':True,
    }
}

def _action_open_window(self, cr, uid, data, context):
    form = data['form']
    cr.execute('select id,name from ir_ui_view where model=%s and type=%s', ('account.move.line', 'form'))
    view_res = cr.fetchone()
    jp = pooler.get_pool(cr.dbname).get('account.journal.period')
    ids = jp.search(cr, uid, [('journal_id','=',form['journal_id']), ('period_id','=',form['period_id'])])
    if not len(ids):
        name = pooler.get_pool(cr.dbname).get('account.journal').read(cr, uid, [form['journal_id']])[0]['name']
        state = pooler.get_pool(cr.dbname).get('account.period').read(cr, uid, [form['period_id']])[0]['state']
        if state == 'done':
            raise wizard.except_wizard(_('UserError'), _('This period is already closed !'))
        company = pooler.get_pool(cr.dbname).get('account.period').read(cr, uid, [form['period_id']])[0]['company_id'][0]
        jp.create(cr, uid, {'name':name, 'period_id': form['period_id'], 'journal_id':form['journal_id'], 'company_id':company})
    ids = jp.search(cr, uid, [('journal_id','=',form['journal_id']), ('period_id','=',form['period_id'])])
    jp = jp.browse(cr, uid, ids, context=context)[0]
    name = (jp.journal_id.code or '') + ':' + (jp.period_id.code or '')

    mod_obj = pooler.get_pool(cr.dbname).get('ir.model.data')
    result = mod_obj._get_id(cr, uid, 'account', 'view_account_move_line_filter')
    id = mod_obj.read(cr, uid, result, ['res_id'])    
    return {
        'domain': "[('journal_id','=',%d), ('period_id','=',%d)]" % (form['journal_id'],form['period_id']),
        'name': name,
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'account.move.line',
        'view_id': view_res,
        'context': "{'journal_id':%d, 'period_id':%d}" % (form['journal_id'],form['period_id']),
        'type': 'ir.actions.act_window',
        'search_view_id': id['res_id']        
    }

class wiz_journal(wizard.interface):
    states = {
        'init': {
            'actions': [_period_get],
            'result': {'type': 'form', 'arch':_journal_form, 'fields':_journal_fields, 'state':[('end','Cancel'),('open','Open Journal')]}
        },
        'open': {
            'actions': [],
            'result': {'type': 'action', 'action': _action_open_window, 'state':'end'}
        }
    }
wiz_journal('account.move.journal')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

