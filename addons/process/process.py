# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import pooler
import tools
from osv import fields, osv

class Env(dict):

    def __init__(self, obj, user):
        self.__obj = obj
        self.__usr = user

    def __getitem__(self, name):
        if name in ('__obj', '__user'):
            return super(Env, self).__getitem__(name)
        if name == 'user':
            return self.__user
        if name == 'object':
            return self.__obj
        return self.__obj[name]

class process_process(osv.osv):
    _name = "process.process"
    _description = "Process"
    _columns = {
        'name': fields.char('Name', size=30,required=True, translate=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the process without removing it."),
        'model_id': fields.many2one('ir.model', 'Object', ondelete='set null'),
        'note': fields.text('Notes', translate=True),
        'node_ids': fields.one2many('process.node', 'process_id', 'Nodes')
    }
    _defaults = {
        'active' : lambda *a: True,
    }

    def search_by_model(self, cr, uid, res_model, context=None):
        pool = pooler.get_pool(cr.dbname)
        model_ids = (res_model or None) and pool.get('ir.model').search(cr, uid, [('model', '=', res_model)])

        domain = (model_ids or []) and [('model_id', 'in', model_ids)]
        result = []

        # search all processes
        res = pool.get('process.process').search(cr, uid, domain)
        if res:
            res = pool.get('process.process').browse(cr, uid, res, context=context)
            for process in res:
                result.append((process.id, process.name))
            return result

        # else search process nodes
        res = pool.get('process.node').search(cr, uid, domain)
        if res:
            res = pool.get('process.node').browse(cr, uid, res, context=context)
            for node in res:
                if (node.process_id.id, node.process_id.name) not in result:
                    result.append((node.process_id.id, node.process_id.name))

        return result

    def graph_get(self, cr, uid, id, res_model, res_id, scale, context=None):

        pool = pooler.get_pool(cr.dbname)

        process = pool.get('process.process').browse(cr, uid, id, context=context)

        name = process.name
        resource = False
        state = 'N/A'

        expr_context = {}
        states = {}
        perm = False

        if res_model:
            states = dict(pool.get(res_model).fields_get(cr, uid, context=context).get('state', {}).get('selection', {}))

        if res_id:
            current_object = pool.get(res_model).browse(cr, uid, res_id, context=context)
            current_user = pool.get('res.users').browse(cr, uid, uid, context=context)
            expr_context = Env(current_object, current_user)
            resource = current_object.name
            if 'state' in current_object:
                state = states.get(current_object.state, 'N/A')
            perm = pool.get(res_model).perm_read(cr, uid, [res_id], context=context)[0]

        notes = process.note or "N/A"
        nodes = {}
        start = []
        transitions = {}

        for node in process.node_ids:
            data = {}
            data['name'] = node.name
            data['model'] = (node.model_id or None) and node.model_id.model
            data['kind'] = node.kind
            data['subflow'] = (node.subflow_id or False) and [node.subflow_id.id, node.subflow_id.name]
            data['notes'] = node.note
            data['active'] = False
            data['gray'] = False
            data['url'] = node.help_url
            data['model_states'] = node.model_states

            # get assosiated workflow
            if data['model']:
                wkf_ids = self.pool.get('workflow').search(cr, uid, [('osv', '=', data['model'])])
                data['workflow'] = (wkf_ids or False) and wkf_ids[0]

            if 'directory_id' in node and node.directory_id:
                data['directory_id'] = node.directory_id.id
                data['directory'] = self.pool.get('document.directory').get_resource_path(cr, uid, data['directory_id'], data['model'], False)

            if node.menu_id:
                data['menu'] = {'name': node.menu_id.complete_name, 'id': node.menu_id.id}

            if node.model_id and node.model_id.model == res_model:
                try:
                    data['active'] = eval(node.model_states, expr_context)
                except Exception:
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
                data['groups'] = groups = []
                for r in tr.transition_ids:
                    if r.group_id:
                        groups.append({'name': r.group_id.name})
                for r in tr.group_ids:
                    groups.append({'name': r.name})
                transitions[tr.id] = data

        # now populate resource information
        def update_relatives(nid, ref_id, ref_model):
            relatives = []

            for dummy, tr in transitions.items():
                if tr['source'] == nid:
                    relatives.append(tr['target'])
                if tr['target'] == nid:
                    relatives.append(tr['source'])

            if not ref_id:
                nodes[nid]['res'] = False
                return

            nodes[nid]['res'] = resource = {'id': ref_id, 'model': ref_model}

            refobj = pool.get(ref_model).browse(cr, uid, ref_id, context=context)
            fields = pool.get(ref_model).fields_get(cr, uid, context=context)

            # check for directory_id from inherited from document module
            if nodes[nid].get('directory_id', False):
                resource['directory'] = self.pool.get('document.directory').get_resource_path(cr, uid, nodes[nid]['directory_id'], ref_model, ref_id)

            resource['name'] = refobj.name_get(context)[0][1]
            resource['perm'] = pool.get(ref_model).perm_read(cr, uid, [ref_id], context)[0]

            ref_expr_context = Env(refobj, current_user)
            try:
                nodes[nid]['active'] = eval(nodes[nid]['model_states'], ref_expr_context)
            except:
                pass 
            for r in relatives:
                node = nodes[r]
                if 'res' not in node:
                    for n, f in fields.items():
                        if node['model'] == ref_model:
                            update_relatives(r, ref_id, ref_model)

                        elif f.get('relation') == node['model']:
                            rel = refobj[n]
                            if rel and isinstance(rel, list) :
                                rel = rel[0]
                            try: # XXX: rel has been reported as string (check it)
                                _id = (rel or False) and rel.id
                                _model = node['model']
                                update_relatives(r, _id, _model)
                            except:
                                pass

        if res_id:
            for nid, node in nodes.items():
                if not node['gray'] and (node['active'] or node['model'] == res_model):
                    update_relatives(nid, res_id, res_model)
                    break

        # calculate graph layout
        g = tools.graph(nodes.keys(), map(lambda x: (x['source'], x['target']), transitions.values()))
        g.process(start)
        g.scale(*scale) #g.scale(100, 100, 180, 120)
        graph = g.result_get()

        # fix the height problem
        miny = -1
        for k,v in nodes.items():
            x = graph[k]['x']
            y = graph[k]['y']
            if miny == -1:
                miny = y
            miny = min(y, miny)
            v['x'] = x
            v['y'] = y

        for k, v in nodes.items():
            y = v['y']
            v['y'] = min(y - miny + 10, y)
        
        nodes = dict([str(n_key), n_val] for n_key, n_val in nodes.iteritems())
        transitions = dict([str(t_key), t_val] for t_key, t_val in transitions.iteritems())
        return dict(name=name, resource=resource, state=state, perm=perm, notes=notes, nodes=nodes, transitions=transitions)

    def copy(self, cr, uid, id, default=None, context=None):
        """ Deep copy the entire process.
        """

        if not default:
            default = {}
        
        pool = pooler.get_pool(cr.dbname)
        process = pool.get('process.process').browse(cr, uid, id, context=context)

        nodes = {}
        transitions = {}

        # first copy all nodes and and map the new nodes with original for later use in transitions
        for node in process.node_ids:
            for t in node.transition_in:
                tr = transitions.setdefault(t.id, {})
                tr['target'] = node.id
            for t in node.transition_out:
                tr = transitions.setdefault(t.id, {})
                tr['source'] = node.id
            nodes[node.id] = pool.get('process.node').copy(cr, uid, node.id, context=context)

        # then copy transitions with new nodes
        for tid, tr in transitions.items():
            vals = {
                'source_node_id': nodes[tr['source']],
                'target_node_id': nodes[tr['target']]
            }
            tr = pool.get('process.transition').copy(cr, uid, tid, default=vals, context=context)

        # and finally copy the process itself with new nodes
        default.update({
            'active': True,
            'node_ids': [(6, 0, nodes.values())]
        })
        return super(process_process, self).copy(cr, uid, id, default, context)

process_process()

class process_node(osv.osv):
    _name = 'process.node'
    _description ='Process Node'
    _columns = {
        'name': fields.char('Name', size=30,required=True, translate=True),
        'process_id': fields.many2one('process.process', 'Process', required=True, ondelete='cascade'),
        'kind': fields.selection([('state','State'), ('subflow','Subflow')], 'Kind of Node', required=True),
        'menu_id': fields.many2one('ir.ui.menu', 'Related Menu'),
        'note': fields.text('Notes', translate=True),
        'model_id': fields.many2one('ir.model', 'Object', ondelete='set null'),
        'model_states': fields.char('States Expression', size=128),
        'subflow_id': fields.many2one('process.process', 'Subflow', ondelete='set null'),
        'flow_start': fields.boolean('Starting Flow'),
        'transition_in': fields.one2many('process.transition', 'target_node_id', 'Starting Transitions'),
        'transition_out': fields.one2many('process.transition', 'source_node_id', 'Ending Transitions'),
        'condition_ids': fields.one2many('process.condition', 'node_id', 'Conditions'),
        'help_url': fields.char('Help URL', size=255)
    }
    _defaults = {
        'kind': lambda *args: 'state',
        'model_states': lambda *args: False,
        'flow_start': lambda *args: False,
    }

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'transition_in': [],
            'transition_out': []
        })
        return super(process_node, self).copy_data(cr, uid, id, default, context=context)

process_node()

class process_node_condition(osv.osv):
    _name = 'process.condition'
    _description = 'Condition'
    _columns = {
        'name': fields.char('Name', size=30, required=True),
        'node_id': fields.many2one('process.node', 'Node', required=True, ondelete='cascade'),
        'model_id': fields.many2one('ir.model', 'Object', ondelete='set null'),
        'model_states': fields.char('Expression', required=True, size=128)
    }
process_node_condition()

class process_transition(osv.osv):
    _name = 'process.transition'
    _description ='Process Transition'
    _columns = {
        'name': fields.char('Name', size=32, required=True, translate=True),
        'source_node_id': fields.many2one('process.node', 'Source Node', required=True, ondelete='cascade'),
        'target_node_id': fields.many2one('process.node', 'Target Node', required=True, ondelete='cascade'),
        'action_ids': fields.one2many('process.transition.action', 'transition_id', 'Buttons'),
        'transition_ids': fields.many2many('workflow.transition', 'process_transition_ids', 'ptr_id', 'wtr_id', 'Workflow Transitions'),
        'group_ids': fields.many2many('res.groups', 'process_transition_group_rel', 'tid', 'rid', string='Required Groups'),
        'note': fields.text('Description', translate=True),
    }
process_transition()

class process_transition_action(osv.osv):
    _name = 'process.transition.action'
    _description ='Process Transitions Actions'
    _columns = {
        'name': fields.char('Name', size=32, required=True, translate=True),
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

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
            
        state = self.pool.get('process.transition.action').browse(cr, uid, id, context=context).state
        if state:
            default['state'] = state

        return super(process_transition_action, self).copy_data(cr, uid, id, default, context)

process_transition_action()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
