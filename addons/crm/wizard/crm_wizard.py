##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
import wizard
import osv
import pooler

section_form = '''<?xml version="1.0"?>
<form string="Create menus for cases">
	<field name="menu_name"/>
	<field name="menu_parent_id"/>
	<field name="section_id"/>
</form>'''

section_fields = {
	'menu_name': {'string':'Menu base name', 'type':'char', 'required':True, 'size':64},
	'menu_parent_id': {'string':'Parent menu', 'type':'many2one', 'relation':'ir.ui.menu'},
	'section_id': {'string':'Case Section', 'type':'many2one', 'relation':'crm.case.section', 'required':True},
}

def case_menu_create(self, cr, uid, data, context):
	pool = pooler.get_pool(cr.dbname)
	pool.get('crm.case.section').menu_create(cr, uid, [data['form']['section_id']], data['form']['menu_name'],  data['form']['menu_parent_id'], context)
	return {}

class wizard_section_menu_create(wizard.interface):
	states = {
		'init': {
			'actions': [], 
			'result': {'type':'form', 'arch':section_form, 'fields':section_fields, 'state':[('end','Cancel'),('create','Create menu Entries')]}
		},
		'create': {
			'actions': [case_menu_create],
			'result': {'type':'state', 'state':'end'}
		}
	}
wizard_section_menu_create('crm.case.section.menu')

