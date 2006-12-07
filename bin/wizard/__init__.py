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

import netsvc
import copy
from tools.misc import UpdateableStr
from tools.translate import translate
from xml import dom

import ir
import pooler

class except_wizard(Exception):
	def __init__(self, name, value):
		self.name = name
		self.value = value

class interface(netsvc.Service):
	states = {}
	
	def __init__(self, name):
		super(interface, self).__init__('wizard.'+name)
		self.exportMethod(self.execute)
		self.wiz_name = name
		
	def translate_view(self, cr, uid, node, state, lang):
		if node.nodeType == node.ELEMENT_NODE:
			if node.hasAttribute('string') and node.getAttribute('string'):
				trans = translate(cr, uid, self.wiz_name+','+state, 'wizard_view', lang, node.getAttribute('string').encode('utf8'))
				if trans:
					node.setAttribute('string', trans.decode('utf8'))
		for n in node.childNodes:
			self.translate_view(cr, uid, n, state, lang)
	
	def execute_cr(self, cr, uid, data, state='init', context={}):
		res = {}
		try:
			state_def = self.states[state]
			result_def = state_def.get('result', {})
			
			actions_res = {}
			# iterate through the list of actions defined for this state
			for action in state_def.get('actions', []):
				# execute them
				action_res = action(self, cr, uid, data, context)
				assert isinstance(action_res, dict), 'The return value of wizard actions should be a dictionary'
				actions_res.update(action_res)
				
			res = copy.copy(result_def)
			res['datas'] = actions_res
			
			lang = context.get('lang', False)
			if result_def['type'] == 'action':
				res['action'] = result_def['action'](self, cr, uid, data, context)
			elif result_def['type'] == 'choice':
				next_state = result_def['next_state'](self, cr, uid, data, context)
				return self.execute_cr(cr, uid, data, next_state, context)
			elif result_def['type'] == 'form':
				fields = copy.copy(result_def['fields'])
				arch = copy.copy(result_def['arch'])
				button_list = copy.copy(result_def['state'])

				# fetch user-set defaut values for the field... shouldn't we pass it the uid?
				defaults = ir.ir_get(cr, uid, 'default', False, [('wizard.'+self.wiz_name, False)])
				default_values = dict([(x[1], x[2]) for x in defaults])
				for val in fields.keys():
					if 'default' in fields[val]:
						# execute default method for this field
						if callable(fields[val]['default']):
							fields[val]['value'] = fields[val]['default'](uid, data, state)
						else:
							fields[val]['value'] = fields[val]['default']
						del fields[val]['default']
					else:
						# if user has set a default value for the field, use it
						if val in default_values:
							fields[val]['value'] = default_values[val]
					if 'selection' in fields[val]:
						if not isinstance(fields[val]['selection'], (tuple, list)):
							fields[val] = copy.copy(fields[val])
							fields[val]['selection'] = fields[val]['selection'](self, cr, uid, context)

				if isinstance(arch, UpdateableStr):
					arch = arch.string
					
				if lang:
					# translate fields
					for field in fields:
						trans = translate(cr, uid, self.wiz_name+','+state+','+field, 'wizard_field', lang)
						if trans:
							fields[field]['string'] = trans

					# translate arch
					if not isinstance(arch, UpdateableStr):
						doc = dom.minidom.parseString(arch)
						self.translate_view(cr, uid, doc, state, lang)
						arch = doc.toxml()

					# translate buttons
					button_list = list(button_list)
					for i, aa  in enumerate(button_list):
						button_name = aa[0]
						trans = translate(cr, uid, self.wiz_name+','+state+','+button_name, 'wizard_button', lang)
						if trans:
							aa = list(aa)
							aa[1] = trans
							button_list[i] = aa
					
				res['fields'] = fields
				res['arch'] = arch
				res['state'] = button_list

		except except_wizard, e:
			self.abortResponse(2, e.name, 'warning', e.value)
			
		return res

	def execute(self, db, uid, data, state='init', context={}):
		cr = pooler.get_db(db).cursor()
		try:
			try:
				res = self.execute_cr(cr, uid, data, state, context)
				cr.commit()
			except Exception:
				cr.rollback()
				raise
		finally:
			cr.close()
		return res
