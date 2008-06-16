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

from osv import fields,osv

def _code_get(self, cr, uid, context={}):
	acc_type_obj = self.pool.get('account.account.type')
	ids = acc_type_obj.search(cr, uid, [])
	res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context)
	return [(r['code'], r['name']) for r in res]


class report_account_receivable(osv.osv):
	_name = "report.account.receivable"
	_description = "Receivable accounts"
	_auto = False
	_columns = {
		'name': fields.char('Week of Year', size=7, readonly=True),
		'type': fields.selection(_code_get, 'Account Type', required=True),
		'balance':fields.float('Balance', readonly=True),
		'debit':fields.float('Debit', readonly=True),
		'credit':fields.float('Credit', readonly=True),
	}
	_order = 'name desc'
	def init(self, cr):
		cr.execute("""
			create or replace view report_account_receivable as (
				select
					min(l.id) as id,
					to_char(date,'YYYY:IW') as name,
					sum(l.debit-l.credit) as balance,
					sum(l.debit) as debit,
					sum(l.credit) as credit,
					a.type
				from
					account_move_line l
				left join
					account_account a on (l.account_id=a.id)
				where
					l.state <> 'draft'
				group by
					to_char(date,'YYYY:IW'), a.type
			)""")
report_account_receivable()

					#a.type in ('receivable','payable')

