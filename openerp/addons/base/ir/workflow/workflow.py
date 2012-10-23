# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc

class workflow(osv.osv):
    _name = "workflow"
    _table = "wkf"
    _order = "name"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'osv': fields.char('Resource Object', size=64, required=True,select=True),
        'on_create': fields.boolean('On Create', select=True),
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

    def get_active_workitems(self, cr, uid, res, res_id, context=None):
        cr.execute('select * from wkf where osv=%s limit 1',(res,))
        wkfinfo = cr.dictfetchone()
        workitems = []
        if wkfinfo:
            cr.execute('SELECT id FROM wkf_instance \
                            WHERE res_id=%s AND wkf_id=%s \
                            ORDER BY state LIMIT 1',
                            (res_id, wkfinfo['id']))
            inst_id = cr.fetchone()

            cr.execute('select act_id,count(*) from wkf_workitem where inst_id=%s group by act_id', (inst_id,))
            workitems = dict(cr.fetchall())
        return {'wkf': wkfinfo, 'workitems':  workitems}

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
    _order = "name"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'wkf_id': fields.many2one('workflow', 'Workflow', required=True, select=True, ondelete='cascade'),
        'split_mode': fields.selection([('XOR', 'Xor'), ('OR','Or'), ('AND','And')], 'Split Mode', size=3, required=True),
        'join_mode': fields.selection([('XOR', 'Xor'), ('AND', 'And')], 'Join Mode', size=3, required=True),
        'kind': fields.selection([('dummy', 'Dummy'), ('function', 'Function'), ('subflow', 'Subflow'), ('stopall', 'Stop All')], 'Kind', size=64, required=True),
        'action': fields.text('Python Action'),
        'action_id': fields.many2one('ir.actions.server', 'Server Action', ondelete='set null'),
        'flow_start': fields.boolean('Flow Start'),
        'flow_stop': fields.boolean('Flow Stop'),
        'subflow_id': fields.many2one('workflow', 'Subflow'),
        'signal_send': fields.char('Signal (subflow.*)', size=32),
        'out_transitions': fields.one2many('workflow.transition', 'act_from', 'Outgoing Transitions'),
        'in_transitions': fields.one2many('workflow.transition', 'act_to', 'Incoming Transitions'),
    }
    _defaults = {
        'kind': lambda *a: 'dummy',
        'join_mode': lambda *a: 'XOR',
        'split_mode': lambda *a: 'XOR',
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None: context = {}
        if not context.get('_force_unlink') and self.pool.get('workflow.workitem').search(cr, uid, [('act_id', 'in', ids)]):
            raise osv.except_osv(_('Operation forbidden'),
                                 _('Please make sure no workitems refer to an activity before deleting it!'))
        super(wkf_activity, self).unlink(cr, uid, ids, context=context)

wkf_activity()

class wkf_transition(osv.osv):
    _table = "wkf_transition"
    _name = "workflow.transition"
    _rec_name = 'signal'
    _columns = {
        'trigger_model': fields.char('Trigger Object', size=128),
        'trigger_expr_id': fields.char('Trigger Expression', size=128),
        'signal': fields.char('Signal (Button Name)', size=64,
                              help="When the operation of transition comes from a button pressed in the client form, "\
                              "signal tests the name of the pressed button. If signal is NULL, no button is necessary to validate this transition."),
        'group_id': fields.many2one('res.groups', 'Group Required',
                                   help="The group that a user must have to be authorized to validate this transition."),
        'condition': fields.char('Condition', required=True, size=128,
                                 help="Expression to be satisfied if we want the transition done."),
        'act_from': fields.many2one('workflow.activity', 'Source Activity', required=True, select=True, ondelete='cascade',
                                    help="Source activity. When this activity is over, the condition is tested to determine if we can start the ACT_TO activity."),
        'act_to': fields.many2one('workflow.activity', 'Destination Activity', required=True, select=True, ondelete='cascade',
                                  help="The destination activity."),
        'wkf_id': fields.related('act_from','wkf_id', type='many2one', relation='workflow', string='Workflow', select=True),
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
        'wkf_id': fields.many2one('workflow', 'Workflow', ondelete='cascade', select=True),
        'res_id': fields.integer('Resource ID'),
        'res_type': fields.char('Resource Object', size=64),
        'state': fields.char('Status', size=32),
    }
    def _auto_init(self, cr, context=None):
        super(wkf_instance, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'wkf_instance_res_type_res_id_state_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX wkf_instance_res_type_res_id_state_index ON wkf_instance (res_type, res_id, state)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'wkf_instance_res_id_wkf_id_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX wkf_instance_res_id_wkf_id_index ON wkf_instance (res_id, wkf_id)')

wkf_instance()

class wkf_workitem(osv.osv):
    _table = "wkf_workitem"
    _name = "workflow.workitem"
    _log_access = False
    _rec_name = 'state'
    _columns = {
        'act_id': fields.many2one('workflow.activity', 'Activity', required=True, ondelete="cascade", select=True),
        'wkf_id': fields.related('act_id','wkf_id', type='many2one', relation='workflow', string='Workflow'),
        'subflow_id': fields.many2one('workflow.instance', 'Subflow', ondelete="cascade", select=True),
        'inst_id': fields.many2one('workflow.instance', 'Instance', required=True, ondelete="cascade", select=True),
        'state': fields.char('Status', size=64, select=True),
    }
wkf_workitem()

class wkf_triggers(osv.osv):
    _table = "wkf_triggers"
    _name = "workflow.triggers"
    _log_access = False
    _columns = {
        'res_id': fields.integer('Resource ID', size=128),
        'model': fields.char('Object', size=128),
        'instance_id': fields.many2one('workflow.instance', 'Destination Instance', ondelete="cascade"),
        'workitem_id': fields.many2one('workflow.workitem', 'Workitem', required=True, ondelete="cascade"),
    }
    def _auto_init(self, cr, context=None):
        super(wkf_triggers, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'wkf_triggers_res_id_model_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX wkf_triggers_res_id_model_index ON wkf_triggers (res_id, model)')
wkf_triggers()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

