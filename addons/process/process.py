# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-TODAY TINY SPRL. (http://tiny.be) All Rights Reserved.
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
import pooler, tools

from osv import fields, osv

class Env(dict):
    
    def __init__(self, obj, user):
        self.__obj = obj
        self.__usr = user
        
    def __getitem__(self, name):
        
        if name in ('__obj', '__user'):
            return super(ExprContext, self).__getitem__(name)
        
        if name == 'user':
            return self.__user
        
        if name == 'object':
            return self.__obj
        
        return self.__obj[name]

class process_process(osv.osv):
    _name = "process.process"
    _description = "Process"
    _columns = {
        'name': fields.char('Name', size=30,required=True),
        'active': fields.boolean('Active'),
        'note': fields.text('Notes'),
        'node_ids': fields.one2many('process.node', 'process_id', 'Nodes')
    }
    _defaults = {
        'active' : lambda *a: True,
    }

    def graph_get(self, cr, uid, id, res_model, res_id, scale, context):
        pool = pooler.get_pool(cr.dbname)
        
        process = pool.get('process.process').browse(cr, uid, [id])[0]
        current_object = pool.get(res_model).browse(cr, uid, [res_id], context)[0]
        current_user = pool.get('res.users').browse(cr, uid, [uid], context)[0]
        
        expr_context = Env(current_object, current_user)
        
        nodes = {}
        start = []
        transitions = {}

        for node in process.node_ids:
            data = {}
            data['name'] = node.name
            data['model'] = (node.model_id or None) and node.model_id.model
            data['kind'] = node.kind
            data['notes'] = node.note
            data['active'] = 0
            data['gray'] = 0

            if node.menu_id:
                data['menu'] = {'name': node.menu_id.complete_name, 'id': node.menu_id.id}
            
            if node.kind == "state" and node.model_id and node.model_id.model == res_model:
                try:
                    if eval(node.model_states, expr_context):
                        data['active'] = current_object.name_get(context)[0][1]
                except Exception, e:
                    # waring: invalid state expression
                    pass
                
            if not data['active']:
                try:
                    gray = True
                    for cond in node.condition_ids:
                        if cond.model_id and cond.model_id.model == res_model:
                            gray = gray and eval(cond.model_states, expr_context)
                    data['gray'] = not gray
                except:
                    pass

            nodes[node.id] = data
            if node.flow_start:
                start.append(node.id)

            for tr in node.transition_out:
                data = {}
                data['name'] = tr.name
                data['source'] = tr.source_node_id.id
                data['target'] = tr.target_node_id.id
                data['notes'] = tr.note
                data['buttons'] = buttons = []
                for b in tr.action_ids:
                    button = {}
                    button['name'] = b.name
                    button['state'] = b.state
                    button['action'] = b.action
                    buttons.append(button)
                data['roles'] = roles = []
                for r in tr.transition_ids:
                    if r.role_id:
                        role = {}
                        role['name'] = r.role_id.name
                        roles.append(role)
                transitions[tr.id] = data

        g = tools.graph(nodes.keys(), map(lambda x: (x['source'], x['target']), transitions.values()))
        g.process(start)
        #g.scale(100, 100, 180, 120)
        g.scale(*scale)
        graph = g.result_get()
        miny = -1

        for k,v in nodes.items():
            x = graph[k]['y']
            y = graph[k]['x']
            if miny == -1:
                miny = y
            miny = min(y, miny)
            v['x'] = x
            v['y'] = y

        for k, v in nodes.items():
            y = v['y']
            v['y'] = min(y - miny + 10, y)
        return dict(nodes=nodes, transitions=transitions)

process_process()

class process_node(osv.osv):
    _name = 'process.node'
    _description ='Process Nodes'
    _columns = {
        'name': fields.char('Name', size=30,required=True),
        'process_id': fields.many2one('process.process', 'Process', required=True),
        'kind': fields.selection([('state','State'), ('subflow','Subflow')], 'Kind of Node', required=True),
        'menu_id': fields.many2one('ir.ui.menu', 'Related Menu'),
        'note': fields.text('Notes'),
        'model_id': fields.many2one('ir.model', 'Object', ondelete='set null'),
        'model_states': fields.char('States Expression', size=128),
        'flow_start': fields.boolean('Starting Flow'),
        'transition_in': fields.one2many('process.transition', 'target_node_id', 'Starting Transitions'),
        'transition_out': fields.one2many('process.transition', 'source_node_id', 'Ending Transitions'),
        'condition_ids': fields.one2many('process.condition', 'node_id', 'Conditions')
    }
    _defaults = {
        'kind': lambda *args: 'state',
        'model_states': lambda *args: False,
        'flow_start': lambda *args: False,
    }
process_node()

class process_node_condition(osv.osv):
    _name = 'process.condition'
    _description = 'Condition'
    _columns = {
        'name': fields.char('Name', size=30, required=True),
        'node_id': fields.many2one('process.node', 'Node', required=True),
        'model_id': fields.many2one('ir.model', 'Object', ondelete='set null'),
        'model_states': fields.char('Expression', required=True, size=128)
    }
process_node_condition()

class process_transition(osv.osv):
    _name = 'process.transition'
    _description ='Process Transitions'
    _columns = {
        'name': fields.char('Name', size=32, required=True),
        'source_node_id': fields.many2one('process.node', 'Source Node', required=True, ondelete='cascade'),
        'target_node_id': fields.many2one('process.node', 'Target Node', required=True, ondelete='cascade'),        
        'action_ids': fields.one2many('process.transition.action', 'transition_id', 'Buttons'),
        'transition_ids': fields.many2many('workflow.transition', 'process_transition_ids', 'ptr_id', 'wtr_id', 'Workflow Transitions'),
        'note': fields.text('Description'),
    }
process_transition()

class process_transition_action(osv.osv):
    _name = 'process.transition.action'
    _description ='Process Transitions Actions'
    _columns = {
        'name': fields.char('Name', size=32, required=True),
        'state': fields.selection([('dummy','Dummy'),
                                   ('object','Object Method'),
                                   ('workflow','Workflow Trigger'),
                                   ('action','Action')], 'Type', required=True),
        'action': fields.char('Action ID', size=64, states={
            'dummy':[('readonly',1)],
            'object':[('required',1)],
            'workflow':[('required',1)],
            'action':[('required',1)],
        },),
        'transition_id': fields.many2one('process.transition', 'Transition', required=True, ondelete='cascade')
    }
    _defaults = {
        'state': lambda *args: 'dummy',
    }
process_transition_action()

