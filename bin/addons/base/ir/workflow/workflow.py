##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields, osv
from tools import graph
import netsvc

class workflow(osv.osv):
	_name = "workflow"
	_table = "wkf"
	_log_access = False
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'osv': fields.char('Resource Model', size=64, required=True),
		'on_create': fields.boolean('On Create'),
		'activities': fields.one2many('workflow.activity', 'wkf_id', 'Activities'),
	}
	_defaults = {
		'on_create': lambda *a: True
	}

	def write(self, cr, user, ids, vals, context=None):
		if not context:
			context={}
		wf_service = netsvc.LocalService("workflow")
		wf_service.clear_cache(cr, user)
		return super(workflow, self).write(cr, user, ids, vals, context=context)

	#
	# scale = [stepx, stepy, posx, posy ]
	#

	def graph_get(self, cr, uid, id, scale, context={}):

		nodes= []
		transitions = []
		start = []
		tres = {}
		workflow = self.browse(cr, uid, id, context)
		for a in workflow.activities:
			nodes.append((a.id,a.name))
			if a.flow_start:
				start.append((a.id,a.name))
			for t in a.out_transitions:
				transitions.append( ((a.id,a.name), (t.act_to.id,t.act_to.name)) )
				tres[t.id] = (a.id,t.act_to.id)
		g  = graph(nodes, transitions)
		g.process(start)
		g.scale(*scale)
		result = g.result_get()
		results = {}


		for r in result.items():
			r[1]['name'] = r[0][1]
			results[str(r[0][0])] = r[1]
		return {'node': results, 'transition': tres}

	def create(self, cr, user, vals, context=None):
		if not context:
			context={}
		wf_service = netsvc.LocalService("workflow")
		wf_service.clear_cache(cr, user)
		return super(workflow, self).create(cr, user, vals, context=context)
workflow()

class wkf_activity(osv.osv):
	_name = "workflow.activity"
	_table = "wkf_activity"
	_log_access = False
	_columns = {
		'name': fields.char('Name', size=64, required=True),
		'wkf_id': fields.many2one('workflow', 'Workflow', required=True, select=True, ondelete='cascade'),
		'split_mode': fields.selection([('XOR', 'Xor'), ('OR','Or'), ('AND','And')], 'Split Mode', size=3, required=True),
		'join_mode': fields.selection([('XOR', 'Xor'), ('AND', 'And')], 'Join Mode', size=3, required=True),
		'kind': fields.selection([('dummy', 'Dummy'), ('function', 'Function'), ('subflow', 'Subflow'), ('stopall', 'Stop All')], 'Kind', size=64, required=True),
		'action': fields.char('Python Action', size=256),
		'action_id': fields.many2one('ir.actions.server', 'Server Action', ondelete='set null'),
		'flow_start': fields.boolean('Flow Start'),
		'flow_stop': fields.boolean('Flow Stop'),
		'subflow_id': fields.many2one('workflow', 'Subflow'),
		'signal_send': fields.char('Signal (subflow.*)', size=32),
		'out_transitions': fields.one2many('workflow.transition', 'act_from', 'Outgoing transitions'),
		'in_transitions': fields.one2many('workflow.transition', 'act_to', 'Incoming transitions'),
	}
	_defaults = {
		'kind': lambda *a: 'dummy',
		'join_mode': lambda *a: 'XOR',
		'split_mode': lambda *a: 'XOR',
	}
wkf_activity()

class wkf_transition(osv.osv):
	_table = "wkf_transition"
	_name = "workflow.transition"
	_log_access = False
	_rec_name = 'signal' #TODO: pas top mais bon...
	_columns = {
		'trigger_model': fields.char('Trigger Type', size=128),
		'trigger_expr_id': fields.char('Trigger Expr ID', size=128),
		'signal': fields.char('Signal (button Name)', size=64),
		'role_id': fields.many2one('res.roles', 'Role Required'),
		'condition': fields.char('Condition', required=True, size=128),
		'act_from': fields.many2one('workflow.activity', 'Source Activity', required=True, select=True, ondelete='cascade'),
		'act_to': fields.many2one('workflow.activity', 'Destination Activity', required=True, select=True, ondelete='cascade'),
	}
	_defaults = {
		'condition': lambda *a: 'True',
	}
wkf_transition()

class wkf_instance(osv.osv):
	_table = "wkf_instance"
	_name = "workflow.instance"
	_rec_name = 'res_type'
	_log_access = False
	_columns = {
		'wkf_id': fields.many2one('workflow', 'Workflow', ondelete='restrict'),
		'uid': fields.integer('User ID'),
		'res_id': fields.integer('Resource ID'),
		'res_type': fields.char('Resource Model', size=64),
		'state': fields.char('State', size=32),
	}
	def _auto_init(self, cr):
		super(wkf_instance, self)._auto_init(cr)
		cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'wkf_instance_res_id_res_type_state_index\'')
		if not cr.fetchone():
			cr.execute('CREATE INDEX wkf_instance_res_id_res_type_state_index ON wkf_instance (res_id, res_type, state)')
			cr.commit()
wkf_instance()

class wkf_workitem(osv.osv):
	_table = "wkf_workitem"
	_name = "workflow.workitem"
	_log_access = False
	_rec_name = 'state'
	_columns = {
		'act_id': fields.many2one('workflow.activity', 'Activity', required=True, ondelete="cascade"),
		'subflow_id': fields.many2one('workflow.instance', 'Subflow', ondelete="cascade"),
		'inst_id': fields.many2one('workflow.instance', 'Instance', required=True, ondelete="cascade", select=1),
		'state': fields.char('State', size=64),
	}
wkf_workitem()

class wkf_triggers(osv.osv):
	_table = "wkf_triggers"
	_name = "workflow.triggers"
	_log_access = False
	_columns = {
		'res_id': fields.integer('Resource ID', size=128),
		'model': fields.char('Model', size=128),
		'instance_id': fields.many2one('workflow.instance', 'Destination Instance', ondelete="cascade"),
		'workitem_id': fields.many2one('workflow.workitem', 'Workitem', required=True, ondelete="cascade"),
	}
	def _auto_init(self, cr):
		super(wkf_triggers, self)._auto_init(cr)
		cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'wkf_triggers_res_id_model_index\'')
		if not cr.fetchone():
			cr.execute('CREATE INDEX wkf_triggers_res_id_model_index ON wkf_triggers (res_id, model)')
			cr.commit()
wkf_triggers()

