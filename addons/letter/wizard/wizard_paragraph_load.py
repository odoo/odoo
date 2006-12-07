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

import wizard
import netsvc

_line_form = '''<?xml version="1.0"?>
<form string="Letter Paragraphs">
	<separator string="Choose Paragraphs to add" colspan="4"/>
	<field name="paragraph_lines" colspan="4" nolabel="1"/>
</form>'''

_line_fields = {
	'paragraph_lines': {'string':'Paragraphs', 'type':'many2many', 'relation':'letter.paragraph'},
}

def _paragraph_find(self, cr, uid, data, context):
	service = netsvc.LocalService("object_proxy")
	type_id = service.execute(cr.dbname, uid, 'letter.letter', 'read', [data['id']], ['type_id'])[0]['type_id'][0]
	para_ids = service.execute(cr.dbname, uid, 'letter.letter.type', 'read', [type_id], ['paragraph_ids'])[0]['paragraph_ids']
	return {'paragraph_lines': para_ids}

def _paragraph_add(self, cr, uid, data, context):
	service = netsvc.LocalService("object_proxy")
	lines = service.execute(cr.dbname, uid, 'letter.paragraph', 'read', data['form']['paragraph_lines'][0][2], ['name','sequence','content','type_id'])
	adding = []
	for line in lines:
		line['letter_id'] = data['id']
		line['type_id'] = line['type_id'][0]
		del line['id']
		adding.append((0,0,line))
	service.execute(cr.dbname, uid, 'letter.letter', 'write', [data['id']], {'paragraph_ids': adding})
	return {}

class paragraph_load(wizard.interface):
	states = {
		'init': {
			'actions': [_paragraph_find],
			'result': {'type':'form', 'arch':_line_form, 'fields':_line_fields, 'state':[('end','Cancel'),('add','Add Paragraphs')]}
		},
		'add': {
			'actions': [_paragraph_add],
			'result': {'type':'state', 'state':'end'}
		}
	}
paragraph_load('letter.paragraph.load')

