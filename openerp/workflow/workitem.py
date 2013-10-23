
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 OpenERP S.A. (<http://openerp.com).
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

#
# TODO:
# cr.execute('delete from wkf_triggers where model=%s and res_id=%s', (res_type,res_id))
#
import logging
import instance

from openerp.workflow.helpers import Session
from openerp.workflow.helpers import Record
from openerp.workflow.helpers import WorkflowActivity

logger = logging.getLogger(__name__)

import openerp
from openerp.tools.safe_eval import safe_eval as eval

class Environment(dict):
    """
    Dictionary class used as an environment to evaluate workflow code (such as
    the condition on transitions).

    This environment provides sybmols for cr, uid, id, model name, model
    instance, column names, and all the record (the one obtained by browsing
    the provided ID) attributes.
    """
    def __init__(self, session, record):
        self.cr = session.cr
        self.uid = session.uid
        self.model = record.model
        self.id = record.id
        self.ids = [record.id]
        self.obj = openerp.registry(self.cr.dbname)[self.model]
        self.columns = self.obj._columns.keys() + self.obj._inherit_fields.keys()

    def __getitem__(self, key):
        if (key in self.columns) or (key in dir(self.obj)):
            res = self.obj.browse(self.cr, self.uid, self.id)
            return res[key]
        else:
            return super(Environment, self).__getitem__(key)

def wkf_expr_eval_expr(session, record, workitem, lines):
    """
    Evaluate each line of ``lines`` with the ``Environment`` environment, returning
    the value of the last line.
    """
    assert lines, 'You used a NULL action in a workflow, use dummy node instead.'
    result = False
    for line in lines.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line == 'True':
            result = True
        elif line == 'False':
            result = False
        else:
            env = Environment(session, record)
            result = eval(line, env, nocopy=True)
    return result

def wkf_expr_execute_action(session, record, workitem, activity):
    """
    Evaluate the ir.actions.server action specified in the activity.
    """
    ir_actions_server = openerp.registry(session.cr.dbname)['ir.actions.server']
    context = { 'active_model': record.model, 'active_id': record.id, 'active_ids': [record.id] }
    result = ir_actions_server.run(session.cr, session.uid, [activity['action_id']], context)
    return result

def wkf_expr_execute(session, record, workitem, activity):
    """
    Evaluate the action specified in the activity.
    """
    return wkf_expr_eval_expr(session, record, workitem, activity['action'])

def wkf_expr_check(session, record, workitem, transition, signal):
    """
    Test if a transition can be taken. The transition can be taken if:

    - the signal name matches,
    - the uid is SUPERUSER_ID or the user groups contains the transition's
      group,
    - the condition evaluates to a truish value.
    """
    if transition['signal'] and signal != transition['signal']:
        return False

    if session.uid != openerp.SUPERUSER_ID and transition['group_id']:
        registry = openerp.registry(session.cr.dbname)
        user_groups = registry['res.users'].read(session.cr, session.uid, [session.uid], ['groups_id'])[0]['groups_id']
        if transition['group_id'] not in user_groups:
            return False

    return wkf_expr_eval_expr(session, record, workitem, transition['condition'])


class WorkflowItem(object):
    def __init__(self, session, record):
        assert isinstance(session, Session)
        assert isinstance(record, Record)
        self.session = session
        self.record = record

    def create(self, activities, instance_id, stack):
        assert isinstance(activities, list)
        assert isinstance(instance_id, (long, int))
        assert isinstance(stack, list)

        cr = self.session.cr
        for activity in activities:
            cr.execute("select nextval('wkf_workitem_id_seq')")
            id_new = cr.fetchone()[0]
            cr.execute("insert into wkf_workitem (id,act_id,inst_id,state) values (%s,%s,%s,'active')", (id_new, activity['id'], instance_id))
            cr.execute('select * from wkf_workitem where id=%s',(id_new,))
            work_item = cr.dictfetchone()
            logger.info('Created workflow item in activity %s',
                        activity['id'],
                        extra={'ident': (self.session.uid, self.record.model, self.record.id)})

            self.process(work_item, stack=stack)

    def process(self, workitem, signal=None, force_running=False, stack=None):
        assert isinstance(workitem, dict)
        assert isinstance(force_running, bool)

        # return _process(self.session, self.record, work_item, signal=signal, force_running=force_running, stack=stack)
        # assert isinstance(force_running, bool)

        assert stack is not None

        cr = self.session.cr

        cr.execute('select * from wkf_activity where id=%s', (workitem['act_id'],))
        activity = cr.dictfetchone()

        triggers = False
        if workitem['state'] == 'active':
            triggers = True
            if not self._execute(workitem, activity, stack):
                return False

        if force_running or workitem['state'] == 'complete':
            ok = self._split_test(workitem, activity['split_mode'], signal, stack)
            triggers = triggers and not ok

        if triggers:
            cr.execute('select * from wkf_transition where act_from=%s', (workitem['act_id'],))
            for trans in cr.dictfetchall():
                if trans['trigger_model']:
                    ids = wkf_expr_eval_expr(self.session, self.record, workitem, trans['trigger_expr_id'])
                    for res_id in ids:
                        cr.execute('select nextval(\'wkf_triggers_id_seq\')')
                        id =cr.fetchone()[0]
                        cr.execute('insert into wkf_triggers (model,res_id,instance_id,workitem_id,id) values (%s,%s,%s,%s,%s)', (trans['trigger_model'],res_id,workitem['inst_id'], workitem['id'], id))

        return True

    def _execute(self, workitem, activity, stack):
        """Send a signal to parenrt workflow (signal: subflow.signal_name)"""
        result = True
        cr = self.session.cr
        signal_todo = []

        if (workitem['state']=='active') and activity['signal_send']:
            # signal_send']:
            cr.execute("select i.id,w.osv,i.res_id from wkf_instance i left join wkf w on (i.wkf_id=w.id) where i.id IN (select inst_id from wkf_workitem where subflow_id=%s)", (workitem['inst_id'],))
            for instance_id, model_name, record_id in cr.fetchall():
                record = Record(model_name, record_id)
                signal_todo.append((instance_id, record, activity['signal_send']))


        if activity['kind'] == WorkflowActivity.KIND_DUMMY:
            if workitem['state']=='active':
                self._state_set(workitem, activity, 'complete')
                if activity['action_id']:
                    res2 = wkf_expr_execute_action(self.session, self.record, workitem, activity)
                    if res2:
                        stack.append(res2)
                        result=res2

        elif activity['kind'] == WorkflowActivity.KIND_FUNCTION:

            if workitem['state']=='active':
                self._state_set(workitem, activity, 'running')
                returned_action = wkf_expr_execute(self.session, self.record, workitem, activity)
                if type(returned_action) in (dict,):
                    stack.append(returned_action)
                if activity['action_id']:
                    res2 = wkf_expr_execute_action(self.session, self.record, workitem, activity)
                    # A client action has been returned
                    if res2:
                        stack.append(res2)
                        result=res2
                self._state_set(workitem, activity, 'complete')

        elif activity['kind'] == WorkflowActivity.KIND_STOPALL:
            if workitem['state']=='active':
                self._state_set(workitem, activity, 'running')
                cr.execute('delete from wkf_workitem where inst_id=%s and id<>%s', (workitem['inst_id'], workitem['id']))
                if activity['action']:
                    wkf_expr_execute(self.session, self.record, workitem, activity)
                self._state_set(workitem, activity, 'complete')

        elif activity['kind'] == WorkflowActivity.KIND_SUBFLOW:

            if workitem['state']=='active':

                self._state_set(workitem, activity, 'running')
                if activity.get('action', False):
                    id_new = wkf_expr_execute(self.session, self.record, workitem, activity)
                    if not id_new:
                        cr.execute('delete from wkf_workitem where id=%s', (workitem['id'],))
                        return False
                    assert type(id_new)==type(1) or type(id_new)==type(1L), 'Wrong return value: '+str(id_new)+' '+str(type(id_new))
                    cr.execute('select id from wkf_instance where res_id=%s and wkf_id=%s', (id_new,activity['subflow_id']))
                    id_new = cr.fetchone()[0]
                else:
                    id_new = instance.create(self.session, self.record, activity['subflow_id'])
                cr.execute('update wkf_workitem set subflow_id=%s where id=%s', (id_new, workitem['id']))
                workitem['subflow_id'] = id_new

            if workitem['state']=='running':
                cr.execute("select state from wkf_instance where id=%s", (workitem['subflow_id'],))
                state= cr.fetchone()[0]
                if state=='complete':
                    self._state_set(workitem, activity, 'complete')

        for instance_id, record, signal_send in signal_todo:
            instance.validate(self.session, self.record, signal_send, force_running=True)

        return result

    def _state_set(self, workitem, activity, state):
        self.session.cr.execute('update wkf_workitem set state=%s where id=%s', (state, workitem['id']))
        workitem['state'] = state
        logger.info('Changed state of work item %s to "%s" in activity %s',
                    workitem['id'], state, activity['id'],
                    extra={'ident': (self.session.uid, self.record.model, self.record.id)})




    def _split_test(self, workitem, split_mode, signal, stack):
        cr = self.session.cr
        cr.execute('select * from wkf_transition where act_from=%s', (workitem['act_id'],))
        test = False
        transitions = []
        alltrans = cr.dictfetchall()

        if split_mode in ('XOR', 'OR'):
            for transition in alltrans:
                if wkf_expr_check(self.session, self.record, workitem, transition,signal):
                    test = True
                    transitions.append((transition['id'], workitem['inst_id']))
                    if split_mode=='XOR':
                        break
        else:
            test = True
            for transition in alltrans:
                if not wkf_expr_check(self.session, self.record, workitem, transition,signal):
                    test = False
                    break
                cr.execute('select count(*) from wkf_witm_trans where trans_id=%s and inst_id=%s', (transition['id'], workitem['inst_id']))
                if not cr.fetchone()[0]:
                    transitions.append((transition['id'], workitem['inst_id']))

        if test and transitions:
            cr.executemany('insert into wkf_witm_trans (trans_id,inst_id) values (%s,%s)', transitions)
            cr.execute('delete from wkf_workitem where id=%s', (workitem['id'],))
            for t in transitions:
                self._join_test(t[0], t[1], stack)
            return True
        return False

    def _join_test(self, trans_id, inst_id, stack):
        cr = self.session.cr
        cr.execute('select * from wkf_activity where id=(select act_to from wkf_transition where id=%s)', (trans_id,))
        activity = cr.dictfetchone()
        if activity['join_mode']=='XOR':
            self.create([activity], inst_id, stack)
            cr.execute('delete from wkf_witm_trans where inst_id=%s and trans_id=%s', (inst_id,trans_id))
        else:
            cr.execute('select id from wkf_transition where act_to=%s', (activity['id'],))
            trans_ids = cr.fetchall()
            ok = True
            for (id,) in trans_ids:
                cr.execute('select count(*) from wkf_witm_trans where trans_id=%s and inst_id=%s', (id,inst_id))
                res = cr.fetchone()[0]
                if not res:
                    ok = False
                    break
            if ok:
                for (id,) in trans_ids:
                    cr.execute('delete from wkf_witm_trans where trans_id=%s and inst_id=%s', (id,inst_id))
                self.create([activity], inst_id, stack)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

