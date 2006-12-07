##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

class actions(osv.osv):
	_name = 'ir.actions.actions'
	_table = 'ir_actions'
	_columns = {
		'name': fields.char('Action Name', required=True, size=64),
		'type': fields.char('Action Type', required=True, size=32),
		'usage': fields.char('Action Usage', size=32)
	}
	_defaults = {
		'usage': lambda *a: False,
	}
actions()

class act_execute(osv.osv):
	_name = 'ir.actions.execute'
	_table = 'ir_act_execute'
	_sequence = 'ir_actions_id_seq'
	_columns = {
		'name': fields.char('name', size=64, required=True, translate=True),
		'type': fields.char('type', size=32, required=True),
		'func_name': fields.char('Function Name', size=64, required=True),
		'func_arg': fields.char('Function Argument', size=64),
		'usage': fields.char('Action Usage', size=32)
	}
act_execute()

class group(osv.osv):
	_name = 'ir.actions.group'
	_table = 'ir_act_group'
	_sequence = 'ir_actions_id_seq'
	_columns = {
		'name': fields.char('Group Name', size=64, required=True),
		'type': fields.char('Action Type', size=32, required=True),
		'exec_type': fields.char('Execution sequence', size=64, required=True),
		'usage': fields.char('Action Usage', size=32)
	}
group()

class report_custom(osv.osv):
	_name = 'ir.actions.report.custom'
	_table = 'ir_act_report_custom'
	_sequence = 'ir_actions_id_seq'
	_columns = {
		'name': fields.char('Report Name', size=64, required=True, translate=True),
		'type': fields.char('Report Type', size=32, required=True),
		'model':fields.char('Model', size=64, required=True),
		'report_id': fields.integer('Report Ref.', required=True),
		'usage': fields.char('Action Usage', size=32)
	}
report_custom()

class report_xml(osv.osv):
	_name = 'ir.actions.report.xml'
	_table = 'ir_act_report_xml'
	_sequence = 'ir_actions_id_seq'
	_columns = {
		'name': fields.char('Name', size=64, required=True, translate=True),
		'type': fields.char('Report Type', size=32, required=True),
		'model': fields.char('Model', size=64, required=True),
		'report_name': fields.char('Internal Name', size=64, required=True),
		'report_xsl': fields.char('XSL path', size=256),
		'report_xml': fields.char('XML path', size=256),
		'report_rml': fields.char('RML path', size=256),
		'auto': fields.boolean('Automatic XSL:RML', required=True),
		'usage': fields.char('Action Usage', size=32)
	}
	_defaults = {
		'type': lambda *a: 'ir.actions.report.xml',
		'auto': lambda *a: True,
	}
report_xml()

class act_window(osv.osv):
	_name = 'ir.actions.act_window'
	_table = 'ir_act_window'
	_sequence = 'ir_actions_id_seq'
	_columns = {
		'name': fields.char('Action Name', size=64, required=True, translate=True),
		'type': fields.char('Action Type', size=32, required=True),
		'view_id': fields.many2one('ir.ui.view', 'View Ref.', ondelete='cascade'),
		'domain': fields.char('Domain Value', size=250),
		'context': fields.char('Context Value', size=250),
		'res_model': fields.char('Model', size=64),
		'view_type': fields.selection((('tree','Tree'),('form','Form')),string='Type of view'),
		'view_mode': fields.selection((('form,list','Form - List'),('list,form','List - Form')), string='Mode of view'),
		'usage': fields.char('Action Usage', size=32)
	}
	_defaults = {
		'type': lambda *a: 'ir.actions.act_window',
		'view_type': lambda *a: 'form',
		'view_mode': lambda *a: 'form,tree',
		'context': lambda *a: '{}'
	}
act_window()

class act_wizard(osv.osv):
	_name = 'ir.actions.wizard'
	_table = 'ir_act_wizard'
	_sequence = 'ir_actions_id_seq'
	_columns = {
		'name': fields.char('Wizard info', size=64, required=True, translate=True),
		'type': fields.char('Action type', size=32, required=True),
		'wiz_name': fields.char('Wizard name', size=64, required=True),
		'multi': fields.boolean('Action on multiple doc.', help="If set to true, the wizard will not be displayed on the right toolbar of a form views.")
	}
	_defaults = {
		'type': lambda *a: 'ir.actions.wizard',
		'multi': lambda *a: False,
	}
act_wizard()

