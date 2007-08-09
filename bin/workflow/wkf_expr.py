##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: wkf_expr.py 1304 2005-09-08 14:35:42Z nicoe $
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
import sys
import netsvc
import osv as base
import pooler


class EnvCall(object):

	def __init__(self,wf_service,d_arg):
		self.wf_service=wf_service
		self.d_arg=d_arg

	def __call__(self,*args):
		arg=self.d_arg+args
		return self.wf_service.execute_cr(*arg)


class Env(dict):

	def __init__(self, wf_service, cr, uid, model, ids):
		self.wf_service = wf_service
		self.cr = cr
		self.uid = uid
		self.model = model
		self.ids = ids
		self.obj = pooler.get_pool(cr.dbname).get(model)
		self.columns = self.obj._columns.keys() + self.obj._inherit_fields.keys()

	def __getitem__(self, key):
		if (key in self.columns) and (not super(Env, self).__contains__(key)):
			res=self.wf_service.execute_cr(self.cr, self.uid, self.model, 'read',\
					self.ids, [key])[0][key]
			super(Env, self).__setitem__(key, res)
			return res
		elif key in dir(self.obj):
			return EnvCall(self.wf_service, (self.cr, self.uid, self.model, key,\
					self.ids))
		else:
			return super(Env, self).__getitem__(key)


def _eval_expr(cr, ident, workitem, action):
	ret=False
	for line in action.split('\n'):
		uid=ident[0]
		model=ident[1]
		ids=[ident[2]]
		if line =='True':
			ret=True
		elif line =='False':
			ret=False
		else:
			wf_service = netsvc.LocalService("object_proxy")
			env = Env(wf_service, cr, uid, model, ids)
			ret = eval(line, env)
	return ret

def execute(cr, ident, workitem, activity):
	return _eval_expr(cr, ident, workitem, activity['action'])

def check(cr, workitem, ident, transition, signal):
	ok = True
	if transition['signal']:
		ok = (signal==transition['signal'])

	if transition['role_id']:
		uid = ident[0]
		serv = netsvc.LocalService('object_proxy')
		user_roles = serv.execute_cr(cr, uid, 'res.users', 'read', [uid], ['roles_id'])[0]['roles_id']
		ok = ok and serv.execute_cr(cr, uid, 'res.roles', 'check', user_roles, transition['role_id'])
	ok = ok and _eval_expr(cr, ident, workitem, transition['condition'])
	return ok

