##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import time
import tools
from osv import fields,osv,orm

import mx.DateTime

MAX_LEVEL = 15
AVAILABLE_STATES = [
	('draft','Draft'),
	('open','Open'),
	('cancel', 'Cancel'),
	('done', 'Close'),
	('pending','Pending')
]

AVAILABLE_PRIORITIES = [
	('5','Lowest'),
	('4','Low'),
	('3','Normal'),
	('2','High'),
	('1','Highest')
]

class crm_case_section(osv.osv):
	_name = "crm.case.section"
	_description = "Case Section"
	_columns = {
		'name': fields.char('Case Section',size=64, required=True),
		'code': fields.char('Section Code',size=8),
		'active': fields.boolean('Active'),
		'sequence': fields.integer('Sequence'),
		'user_id': fields.many2one('res.users', 'Responsible'),
		'reply_to': fields.char('Reply-To', size=64, help="The email address wich is the 'Reply-To' of all email sent by Tiny ERP for cases in this section"),
		'parent_id': fields.many2one('crm.case.section', 'Parent Section'),
		'child_ids': fields.one2many('crm.case.section', 'parent_id', 'Childs Sections'),
	}
	_defaults = {
		'active': lambda *a: 1,
	}
	_sql_constraints = [
		('code_uniq', 'unique (code)', 'The code of the section must be unique !')
	]
	def menu_create(self, cr, uid, ids, name, menu_parent_id=False, context={}):
		menus = {}
		menus[-1] = menu_parent_id
		for section in self.browse(cr, uid, ids, context):
			for (index, mname, mdomain, latest) in [
				(0,'',"[('section_id','=',"+str(section.id)+")]", -1),
				(1,'My ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid)]", 0),
				(2,'My Unclosed ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','<>','cancel'), ('state','<>','close')]", 1),
				(5,'My Open ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','=','open')]", 2),
				(6,'My Pending ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','=','pending')]", 2),
				(7,'My Draft ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','=','draft')]", 2),

				(3,'My Late ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('date_deadline','<=',time.strftime('%Y-%m-%d')), ('state','<>','cancel'), ('state','<>','close')]", 1),
				(4,'My Canceled ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('state','=','cancel')]", 1),
				(8,'All ',"[('section_id','=',"+str(section.id)+"),]", 0),
				(9,'Unassigned ',"[('section_id','=',"+str(section.id)+"),('user_id','=',False)]", 8),
				(10,'Late ',"[('section_id','=',"+str(section.id)+"),('user_id','=',uid), ('date_deadline','<=',time.strftime('%Y-%m-%d')), ('state','<>','cancel'), ('state','<>','close')]", 8),
				(11,'Canceled ',"[('section_id','=',"+str(section.id)+"),('state','=','cancel')]", 8),
				(12,'Unclosed ',"[('section_id','=',"+str(section.id)+"),('state','<>','cancel'), ('state','<>','close')]", 8),
				(13,'Open ',"[('section_id','=',"+str(section.id)+"),('state','=','open')]", 12),
				(14,'Pending ',"[('section_id','=',"+str(section.id)+"),('state','=','pending')]", 12),
				(15,'Draft ',"[('section_id','=',"+str(section.id)+"),('state','=','draft')]", 12),
			]:
				view_mode = 'tree,form'
				icon = 'STOCK_JUSTIFY_FILL'
				if index==0:
					view_mode = 'form,tree'
					icon = 'STOCK_NEW'
				menu_id=self.pool.get('ir.ui.menu').create(cr, uid, {
					'name': mname+name,
					'parent_id': menus[latest],
					'icon': icon
				})
				menus[index] = menu_id
				action_id = self.pool.get('ir.actions.act_window').create(cr,uid, {
					'name': 'Action '+mname+name+' Cases',
					'res_model': 'crm.case',
					'domain': mdomain,
					'view_type': 'form',
					'view_mode': view_mode,
				})
				self.pool.get('ir.values').create(cr, uid, {
					'name': 'Open Cases',
					'key2': 'tree_but_open',
					'model': 'ir.ui.menu',
					'res_id': menu_id,
					'value': 'ir.actions.act_window,%d'%action_id,
					'object': True
				})
		return True
	def name_get(self, cr, uid, ids, context={}):
		if not len(ids):
			return []
		reads = self.read(cr, uid, ids, ['name','parent_id'], context)
		res = []
		for record in reads:
			name = record['name']
			if record['parent_id']:
				name = record['parent_id'][1]+' / '+name
			res.append((record['id'], name))
		return res
crm_case_section()

class crm_case_categ(osv.osv):
	_name = "crm.case.categ"
	_description = "Category of case"
	_columns = {
		'name': fields.char('Case Category Name', size=64, required=True),
		'probability': fields.float('Probability', required=True),
		'section_id': fields.many2one('crm.case.section', 'Case Section'),
	}
	_defaults = {
		'probability': lambda *args: 0.0
	}
crm_case_categ()

class crm_case_rule(osv.osv):
	_name = "crm.case.rule"
	_description = "Case Rule"
	_columns = {
		'name': fields.char('Rule Name',size=64, required=True),
		'active': fields.boolean('Active'),
		'sequence': fields.integer('Sequence'),

		'trg_state_from': fields.selection([('',''),('escalate','Escalate')]+AVAILABLE_STATES, 'Case state from', size=16),
		'trg_state_to': fields.selection([('',''),('escalate','Escalate')]+AVAILABLE_STATES, 'Case state to', size=16),

		'trg_date_type':  fields.selection([
			('none','None'),
			('create','Creation Date'),
			('action_last','Last Action Date'),
			('deadline','Deadline'),
			], 'Trigger Date', size=16),
		'trg_date_range': fields.integer('Delay after trigger date'),
		'trg_date_range_type': fields.selection([('hour','Hours'),('day','Days'),('month','Months')], 'Delay type'),

		'trg_section_id': fields.many2one('crm.case.section', 'Section'),
		'trg_categ_id':  fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',trg_section_id)]"),
		'trg_user_id':  fields.many2one('res.users', 'Responsible'),

		'trg_partner_id': fields.many2one('res.partner', 'Partner'),
		'trg_partner_categ_id': fields.many2one('res.partner.category', 'Partner Category'),

		'trg_priority_from': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Priority min'),
		'trg_priority_to': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Priority max'),

		'act_method': fields.char('Call Object Method', size=64),
		'act_state': fields.selection([('','')]+AVAILABLE_STATES, 'Set state to', size=16),
		'act_section_id': fields.many2one('crm.case.section', 'Set section to'),
		'act_user_id': fields.many2one('res.users', 'Set responsible to'),
		'act_priority': fields.selection([('','')] + AVAILABLE_PRIORITIES, 'Set priority to'),
		'act_email_cc': fields.char('Add watchers (Cc)', size=250),

		'act_remind_partner': fields.boolean('Remind partner'),
		'act_remind_user': fields.boolean('Remind responsible'),

		'act_mail_to_user': fields.boolean('Mail to responsible'),
		'act_mail_to_partner': fields.boolean('Mail to partner'),
		'act_mail_to_watchers': fields.boolean('Mail to watchers (Cc)'),
		'act_mail_to_email': fields.char('Mail to these emails', size=128),
		'act_mail_body': fields.text('Mail body')
	}
	_defaults = {
		'active': lambda *a: 1,
		'trg_date_type': lambda *a: 'none',
		'trg_date_range_type': lambda *a: 'day',
		'act_mail_to_user': lambda *a: 0,
		'act_remind_partner': lambda *a: 0,
		'act_remind_user': lambda *a: 0,
		'act_mail_to_partner': lambda *a: 0,
		'act_mail_to_watchers': lambda *a: 0,
	}
	_order = 'sequence'
	#
	# Function called by the sceduler to proccess cases for date actions
	# Only works on not done and canceled cases
	#
	def _check(self, cr, uid, ids=False, context={}):
		cr.execute('select * from crm_case where (date_action_last<%s or date_action_last is null) and (date_action_next<=%s or date_action_next is null) and state not in (\'cancel\',\'done\')', (time.strftime("%Y-%m-%d %H:%M:%S"), time.strftime('%Y-%m-%d %H:%M:%S')) )
		ids2 = map(lambda x: x[0], cr.fetchall() or [])
		case_obj = self.pool.get('crm.case')
		cases = case_obj.browse(cr, uid, ids2, context)
		return case_obj._action(cr, uid, cases, False, context=context)
crm_case_rule()

def _links_get(self, cr, uid, context={}):
	obj = self.pool.get('res.request.link')
	ids = obj.search(cr, uid, [])
	res = obj.read(cr, uid, ids, ['object', 'name'], context)
	return [(r['object'], r['name']) for r in res]

class crm_case(osv.osv):
	_name = "crm.case"
	_description = "Case"
	_columns = {
		'id': fields.integer('Case ID', readonly=True),
		'name': fields.char('Case Description',size=64, required=True),
		'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
		'active': fields.boolean('Active'),
		'description': fields.text('Description'),
		'section_id': fields.many2one('crm.case.section', 'Case Section', required=True),
		'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id)]", relate=True),
		'planned_revenue': fields.float('Planned Revenue'),
		'planned_cost': fields.float('Planned Costs'),
		'probability': fields.float('Probability (0.50)'),
		'email_from': fields.char('Partner Email', size=128),
		'email_cc': fields.char('Watchers Emails', size=252),
		'email_last': fields.text('Latest E-Mail'),
		'partner_id': fields.many2one('res.partner', 'Partner', relate=True),
		'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', domain="[('partner_id','=',partner_id)]"),
		'som': fields.many2one('res.partner.som', 'State of Mind'),
		'date': fields.datetime('Date'),
		'create_date': fields.datetime('Date Created'),
		'date_deadline': fields.date('Date Deadline'),
		'date_closed': fields.datetime('Date Closed', readonly=True),
		'canal_id': fields.many2one('res.partner.canal', 'Channel', relate=True),
		'user_id': fields.many2one('res.users', 'User Responsible', relate=True),
		'history_line': fields.one2many('crm.case.history', 'case_id', 'Case History'),
		'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
		'ref' : fields.reference('Reference', selection=_links_get, size=128),
		'ref2' : fields.reference('Reference 2', selection=_links_get, size=128),

		'date_action_last': fields.datetime('Date Last Action', readonly=1),
		'date_action_next': fields.datetime('Date Next Action', readonly=1),
	}
	_defaults = {
		'active': lambda *a: 1,
		'user_id': lambda s,cr,uid,c={}: uid,
		'state': lambda *a: 'draft',
		'priority': lambda *a: AVAILABLE_PRIORITIES[1][0],
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
	}
	_order = 'priority, date_deadline, id'
	def _action(self, cr, uid, cases, state_to, scrit=[], context={}):
		action_ids = self.pool.get('crm.case.rule').search(cr, uid, scrit)
		level = MAX_LEVEL
		while len(action_ids) and level:
			newactions = []
			actions = self.pool.get('crm.case.rule').browse(cr, uid, action_ids, context)
			for case in cases:
				for action in actions:
					ok = True
					ok = ok and (not action.trg_state_from or action.trg_state_from==case.state)
					ok = ok and (not action.trg_state_to or action.trg_state_to==state_to)
					ok = ok and (not action.trg_section_id or action.trg_section_id.id==case.section_id.id)
					ok = ok and (not action.trg_categ_id or action.trg_categ_id.id==case.categ_id.id)
					ok = ok and (not action.trg_user_id.id or action.trg_user_id.id==case.user_id.id)
					ok = ok and (not action.trg_partner_id.id or action.trg_partner_id.id==case.partner_id.id)
					ok = ok and (
						not action.trg_partner_categ_id.id or 
						(
							case.partner_id.id and
							(action.trg_partner_categ_id.id in map(lambda x: x.id, case.partner_id.category_id or []))
						)
					)
					ok = ok and (not action.trg_priority_from or action.trg_priority_from<=case.priority)
					ok = ok and (not action.trg_priority_to or action.trg_priority_to>=case.priority)
					if not ok:
						continue

					base = False
					if action.trg_date_type=='create':
						base = mx.DateTime.strptime(case.create_date[:19], '%Y-%m-%d %H:%M:%S')
					elif action.trg_date_type=='action_last':
						if case.date_action_last:
							base = mx.DateTime.strptime(case.date_action_last, '%Y-%m-%d %H:%M:%S')
						else:
							base = mx.DateTime.strptime(case.create_date[:19], '%Y-%m-%d %H:%M:%S')
					elif action.trg_date_type=='deadline':
						base = mx.DateTime.strptime(case.date_deadline, '%Y-%m-%d')
					if base:
						fnct = {
							'day': lambda interval: mx.DateTime.RelativeDateTime(days=interval),
							'hour': lambda interval: mx.DateTime.RelativeDateTime(hours=interval),
							'month': lambda interval: mx.DateTime.RelativeDateTime(months=interval),
						}
						d = base + fnct[action.trg_date_range_type](action.trg_date_range)
						dt = d.strftime('%Y-%m-%d %H:%M:%S')
						ok = (dt <= time.strftime('%Y-%m-%d %H:%M:%S')) and ((not case.date_action_next) or dt>case.date_action_next)
						if not ok:
							if not case.date_action_next or dt<case.date_action_next:
								case.date_action_next = dt
								self.write(cr, uid, [case.id], {'date_action_next': dt}, context)

					else:
						ok = action.trg_date_type=='none'

					if ok:
						write = {}
						if action.act_state:
							write['state'] = action.act_state
						if action.act_section_id:
							write['section_id'] = action.act_section_id.id
						if action.act_user_id:
							write['user_id'] = action.act_user_id.id
						if action.act_priority:
							write['priority'] = action.act_priority
						if action.act_email_cc:
							if '@' in (case.email_cc or ''):
								write['email_cc'] = case.email_cc+','+action.act_email_cc
							else:
								write['email_cc'] = action.act_email_cc
						write['date_action_last'] = time.strftime('%Y-%m-%d %H:%M:%S')
						self.write(cr, uid, [case.id], write, context)
						caseobj = self.pool.get('crm.case')
						if action.act_remind_user:
							caseobj.remind_user(cr, uid, [case.id], context)
						if action.act_remind_partner:
							caseobj.remind_partner(cr, uid, [case.id], context)
						if action.act_method:
							getattr(caseobj, 'act_method')(cr, uid, [case.id], action, context)
						emails = []
						if action.act_mail_to_user:
							if case.user_id and case.user_id.address_id:
								emails.append(case.user_id.address_id.email)
						if action.act_mail_to_partner:
							emails.append(case.email_from)
						if action.act_mail_to_watchers:
							emails += (case.email_cc or '').split(',')
						if action.act_mail_to_email:
							emails += (action.act_mail_to_email or '').split(',')
						emails = filter(None, emails)
						if len(emails) and action.act_mail_body:
							self.email_send(cr, uid, case, emails, action.act_mail_body)
						break
			action_ids = newactions
			level -= 1
		return True

	def email_send(self, cr, uid, case, emails, body, context={}):
		data = {
			'case_id': case.id,
			'case_subject': case.name,
			'case_date': case.date,

			'case_user': case.user_id.name or '/',
			'case_user_email': case.user_id.address_id.email,
			'case_user_phone': case.user_id.address_id.phone,

			'email_from': case.email_from,
			'partner': (case.partner_id and case.partner_id.name) or '/',
			'partner_email': (case.partner_address_id and case.partner_address_id.email) or '/',
		}
		body = body % data
		tools.email_send(case.user_id.address_id.email, emails, '['+str(case.id)+'] '+case.name, body, reply_to=case.section_id.reply_to)
		return True
	def __log(self, cr, uid, cases, keyword, context={}):
		if not self.pool.get('res.partner.event.type').check(cr, uid, 'crm_case_'+keyword):
			return False
		for case in cases:
			if case.partner_id:
				self.pool.get('res.partner.event').create(cr, uid, {
					'name':'Case '+keyword+': '+case.name,
					'som':(case.som or False) and case.som.id,
					'description':case.description,
					'partner_id':case.partner_id.id,
					'date':case.date,
					'canal_id':(case.canal_id or False) and case.canal_id.id,
					'user_id':uid,
				})
		return True

	def __history(self, cr, uid, cases, keyword, context={}):
		for case in cases:
			self.pool.get('crm.case.history').create(cr, uid, {
				'name': keyword,
				'description': case.description,
				'som': False,
				'canal_id': False,
				'user_id': uid,
				'case_id': case.id
			})
		return True

	def create(self, cr, uid, *args, **argv):
		res = super(crm_case, self).create(cr, uid, *args, **argv)
		cases = self.browse(cr, uid, [res])
		self.__log(cr,uid, cases, 'draft')
		self._action(cr,uid, cases, 'draft')
		return res

	def remind_partner(self, cr, uid, ids, *args):
		for case in self.browse(cr, uid, ids):
			if case.user_id and case.user_id.address_id and case.user_id.address_id.email and case.email_from:
				tools.email_send(
					case.user_id.address_id.email,
					[case.email_from],
					'Reminder: '+'['+str(case.id)+']'+' '+case.name,
					case.email_last or case.description, reply_to=case.section_id.reply_to
					)
		return True

	def remind_user(self, cr, uid, ids, *args):
		for case in self.browse(cr, uid, ids):
			if case.user_id and case.user_id.address_id and case.user_id.address_id.email and case.email_from:
				tools.email_send(
					case.email_from,
					[case.user_id.address_id.email],
					'Reminder: '+'['+str(case.id)+']'+' '+case.name,
					case.email_last or case.description, reply_to=case.section_id.reply_to
					)
		return True

	def case_log(self, cr, uid, ids, *args):
		cases = self.browse(cr, uid, ids)
		self.__history(cr, uid, cases, '')
		return self.write(cr, uid, ids, {'description':False, 'som':False, 'canal_id': False})

	def case_log_reply(self, cr, uid, ids, *args):
		cases = self.browse(cr, uid, ids)
		for case in cases:
			if not case.email_from:
				raise osv.except_osv('Error !', 'You must put a Partner eMail to use this action !')
		self.__history(cr, uid, cases, '')
		for case in cases:
			self.write(cr, uid, [case.id], {'description':False, 'som':False, 'canal_id': False, 'email_last':case.description})
			emails = [case.email_from] + (case.email_cc or '').split(',')
			emails = filter(None, emails)
			tools.email_send(case.user_id.address_id.email, emails, '['+str(case.id)+'] '+case.name, case.description, reply_to=case.section_id.reply_to)
		return True

	def onchange_partner_id(self, cr, uid, ids, part, email=False):
		if not part:
			return {'value':{'partner_address_id': False}}
		addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['contact'])
		data = {'partner_address_id':addr['contact']}
		if addr['contact'] and not email:
			data['email_from'] = self.pool.get('res.partner.address').browse(cr, uid, addr['contact']).email
		return {'value':data}

	def onchange_categ_id(self, cr, uid, ids, categ, context={}):
		if not categ:
			return {'value':{}}
		cat = self.pool.get('crm.case.categ').browse(cr, uid, categ, context).probability
		return {'value':{'probability':cat}}


	def onchange_partner_address_id(self, cr, uid, ids, part, email=False):
		if not part:
			return {'value':{}}
		data = {}
		if not email:
			data['email_from'] = self.pool.get('res.partner.address').browse(cr, uid, part).email
		return {'value':data}

	def case_close(self, cr, uid, ids, *args):
		cases = self.browse(cr, uid, ids)
		self.__log(cr,uid, cases, 'close')
		self.__history(cr, uid, cases, 'Close')
		self.write(cr, uid, ids, {'state':'done', 'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')})
		#
		# We use the cache of cases to keep the old case state
		#
		self._action(cr,uid, cases, 'done')
		return True

	def case_escalate(self, cr, uid, ids, *args):
		cases = self.browse(cr, uid, ids)
		for case in cases:
			data = {'active':True, 'user_id': False}
			if case.section_id.parent_id:
				data['section_id'] = case.section_id.parent_id.id
			else:
				raise osv.except_osv('Error !', 'You can not escalate this case.\nYou are already at the top level.')
			self.write(cr, uid, ids, data)
		self.__history(cr, uid, cases, 'escalate')
		self._action(cr, uid, cases, 'escalate')
		return True


	def case_open(self, cr, uid, ids, *args):
		cases = self.browse(cr, uid, ids)
		self.__log(cr, uid, cases, 'open')
		self.__history(cr, uid, cases, 'Open')
		for case in cases:
			data = {'state':'open', 'active':True}
			if not case.user_id:
				data['user_id'] = uid
			self.write(cr, uid, ids, data)
		self._action(cr,uid, cases, 'open')
		return True

	def emails_get(self, cr, uid, id, context={}):
		case = self.browse(cr, uid, id)
		return ((case.user_id and case.user_id.address_id and case.user_id.address_id.email) or False, case.email_from, case.email_cc, case.priority)

	def case_cancel(self, cr, uid, ids, *args):
		cases = self.browse(cr, uid, ids)
		self.__log(cr, uid, cases, 'cancel')
		self.__history(cr, uid, cases, 'Cancel')
		self.write(cr, uid, ids, {'state':'cancel', 'active':True})
		self._action(cr,uid, cases, 'cancel')
		return True

	def case_pending(self, cr, uid, ids, *args):
		cases = self.browse(cr, uid, ids)
		self.__log(cr, uid, cases, 'pending')
		self.__history(cr, uid, cases, 'Pending')
		self.write(cr, uid, ids, {'state':'pending', 'active':True})
		self._action(cr,uid, cases, 'pending')
		return True

	def case_reset(self, cr, uid, ids, *args):
		cases = self.browse(cr, uid, ids)
		self.__log(cr, uid, cases, 'draft')
		self.__history(cr, uid, cases, 'Draft')
		self.write(cr, uid, ids, {'state':'draft', 'active':True})
		self._action(cr, uid, cases, 'draft')
		return True
crm_case()

class crm_case_history(osv.osv):
	_name = "crm.case.history"
	_description = "Case history"
	_columns = {
		'name': fields.char('Name', size=64),
		'description': fields.text('Description'),
		'som': fields.many2one('res.partner.som', 'State of Mind'),
		'date': fields.date('Date'),
		'canal_id': fields.many2one('res.partner.canal', 'Channel'),
		'user_id': fields.many2one('res.users', 'User Responsible', readonly=True),
		'case_id': fields.many2one('crm.case', 'Case', required=True, ondelete='cascade')
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
	}
crm_case_history()

