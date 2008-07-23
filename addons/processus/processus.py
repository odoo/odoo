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
from osv import fields, osv


class processus_processus(osv.osv):
    _name = "processus.processus"
    _description = "Processus"
    _columns = {
        'name': fields.char('Processus', size=30,required=True),
        'active': fields.boolean('Active'),
        'note': fields.text('Notes'),
        'node_ids': fields.one2many('processus.node', 'processus_id', 'Nodes')
    }
    _defaults = {
        'active' : lambda *a: True,
    }
processus_processus()

class processus_node(osv.osv):
    _name = 'processus.node'
    _description ='Processus Nodes'
    _columns = {
        'name': fields.char('Processus', size=30,required=True),
        'processus_id': fields.many2one('processus.processus', 'Processus', required=True),
        'kind': fields.selection([('state','State'),('router','Router'),('subflow','Subflow')],'Kind of Node', required=True),
        'menu_id': fields.many2one('ir.ui.menu', 'Related Menu'),
        'note': fields.text('Notes'),
        'model_id': fields.many2one('ir.model', 'Model', ondelete='set null'),
        'model_states': fields.char('States Expression', size=128),
        'flow_start': fields.boolean('Starting Flow'),
        'transition_in': fields.one2many('processus.transition', 'node_to_id', 'Starting Transitions'),
        'transition_out': fields.one2many('processus.transition', 'node_from_id', 'Ending Transitions'),
    }
    _defaults = {
        'kind': lambda *args: 'state',
        'model_states': lambda *args: False,
        'flow_start': lambda *args: False,
    }
processus_node()

class processus_transition(osv.osv):
    _name = 'processus.transition'
    _description ='Processus Transitions'
    _columns = {
        'name': fields.char('Transitions', size=32, required=True),
        'node_from_id': fields.many2one('processus.node', 'Origin Node', required=True, ondelete='cascade'),
        'node_to_id': fields.many2one('processus.node', 'Destination Node', required=True, ondelete='cascade'),
        'transition_ids': fields.many2many('workflow.transition', 'processus_transition_ids', 'trans1_id', 'trans2_id', 'Workflow Transitions'),
        'note': fields.text('Description'),
        'action_ids': fields.one2many('processus.transition.action', 'transition_id', 'Buttons')
    }
    _defaults = {
    }
processus_transition()

class processus_transition_action(osv.osv):
    _name = 'processus.transition.action'
    _description ='Processus Transitions Actions'
    _columns = {
        'name': fields.char('Transitions', size=32, required=True),
        'state': fields.selection([('dummy','Dummy'),('method','Object Method'),('workflow','Workflow Trigger'),('action','Action')], 'Type', required=True),
        'action': fields.char('Action ID', size=64, states={
            'dummy':[('readonly',1)],
            'method':[('required',1)],
            'workflow':[('required',1)],
            'action':[('required',1)],
        },),
        'transition_id': fields.many2one('processus.transition', 'Transition', required=True, ondelete='cascade')
    }
    _defaults = {
        'state': lambda *args: 'dummy',
    }
processus_transition_action()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

