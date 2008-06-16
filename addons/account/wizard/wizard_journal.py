##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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
from osv import osv
import pooler

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
			raise wizard.except_wizard('UserError', 'This period is already closed !')
		jp.create(cr, uid, {'name':name, 'period_id': form['period_id'], 'journal_id':form['journal_id']})
	ids = jp.search(cr, uid, [('journal_id','=',form['journal_id']), ('period_id','=',form['period_id'])])
	jp = jp.browse(cr, uid, ids, context=context)[0]
	name = (jp.journal_id.code or '') + ':' + (jp.period_id.code or '')
	return {
		'domain': "[('journal_id','=',%d), ('period_id','=',%d)]" % (form['journal_id'],form['period_id']),
		'name': name,
		'view_type': 'form',
		'view_mode': 'tree,form',
		'res_model': 'account.move.line',
		'view_id': view_res,
		'context': "{'journal_id':%d, 'period_id':%d}" % (form['journal_id'],form['period_id']),
		'type': 'ir.actions.act_window'
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

