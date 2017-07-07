
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def __getitem__(self, key):
        records = self.obj.browse(self.cr, self.uid, self.ids)
        if hasattr(records, key):
            return getattr(records, key)
        else:
            return super(Environment, self).__getitem__(key)


class WorkflowItem(object):
    def __init__(self, session, record, work_item_values):
        assert isinstance(session, Session)
        assert isinstance(record, Record)
        self.session = session
        self.record = record

        if not work_item_values:
            work_item_values = {}

        assert isinstance(work_item_values, dict)
        self.workitem = work_item_values

    @classmethod
    def create(cls, session, record, activity, instance_id, stack):
        assert isinstance(session, Session)
        assert isinstance(record, Record)
        assert isinstance(activity, dict)
        assert isinstance(instance_id, (long, int))
        assert isinstance(stack, list)

        cr = session.cr
        cr.execute("select nextval('wkf_workitem_id_seq')")
        id_new = cr.fetchone()[0]
        cr.execute("insert into wkf_workitem (id,act_id,inst_id,state) values (%s,%s,%s,'active')", (id_new, activity['id'], instance_id))
        cr.execute('select * from wkf_workitem where id=%s',(id_new,))
        work_item_values = cr.dictfetchone()
        logger.info('Created workflow item in activity %s',
                    activity['id'],
                    extra={'ident': (session.uid, record.model, record.id)})

        workflow_item = WorkflowItem(session, record, work_item_values)
        workflow_item.process(stack=stack)

    @classmethod
    def create_all(cls, session, record, activities, instance_id, stack):
        assert isinstance(activities, list)

        for activity in activities:
            cls.create(session, record, activity, instance_id, stack)

    def process(self, signal=None, force_running=False, stack=None):
        assert isinstance(force_running, bool)
        assert stack is not None

        cr = self.session.cr

        cr.execute('select * from wkf_activity where id=%s', (self.workitem['act_id'],))
        activity = cr.dictfetchone()

        triggers = False
        if self.workitem['state'] == 'active':
            triggers = True
            if not self._execute(activity, stack):
                return False

        if force_running or self.workitem['state'] == 'complete':
            ok = self._split_test(activity['split_mode'], signal, stack)
            triggers = triggers and not ok

        if triggers:
            cr.execute('select * from wkf_transition where act_from=%s ORDER BY sequence,id', (self.workitem['act_id'],))
            for trans in cr.dictfetchall():
                if trans['trigger_model']:
                    ids = self.wkf_expr_eval_expr(trans['trigger_expr_id'])
                    for res_id in ids:
                        cr.execute('select nextval(\'wkf_triggers_id_seq\')')
                        id =cr.fetchone()[0]
                        cr.execute('insert into wkf_triggers (model,res_id,instance_id,workitem_id,id) values (%s,%s,%s,%s,%s)', (trans['trigger_model'],res_id, self.workitem['inst_id'], self.workitem['id'], id))

        return True

    def _execute(self, activity, stack):
        """Send a signal to parenrt workflow (signal: subflow.signal_name)"""
        result = True
        cr = self.session.cr
        signal_todo = []

        if (self.workitem['state']=='active') and activity['signal_send']:
            # signal_send']:
            cr.execute("select i.id,w.osv,i.res_id from wkf_instance i left join wkf w on (i.wkf_id=w.id) where i.id IN (select inst_id from wkf_workitem where subflow_id=%s)", (self.workitem['inst_id'],))
            for instance_id, model_name, record_id in cr.fetchall():
                record = Record(model_name, record_id)
                signal_todo.append((instance_id, record, activity['signal_send']))


        if activity['kind'] == WorkflowActivity.KIND_DUMMY:
            if self.workitem['state']=='active':
                self._state_set(activity, 'complete')
                if activity['action_id']:
                    res2 = self.wkf_expr_execute_action(activity)
                    if res2:
                        stack.append(res2)
                        result=res2

        elif activity['kind'] == WorkflowActivity.KIND_FUNCTION:

            if self.workitem['state']=='active':
                self._state_set(activity, 'running')
                returned_action = self.wkf_expr_execute(activity)
                if type(returned_action) in (dict,):
                    stack.append(returned_action)
                if activity['action_id']:
                    res2 = self.wkf_expr_execute_action(activity)
                    # A client action has been returned
                    if res2:
                        stack.append(res2)
                        result=res2
                self._state_set(activity, 'complete')

        elif activity['kind'] == WorkflowActivity.KIND_STOPALL:
            if self.workitem['state']=='active':
                self._state_set(activity, 'running')
                cr.execute('delete from wkf_workitem where inst_id=%s and id<>%s', (self.workitem['inst_id'], self.workitem['id']))
                if activity['action']:
                    self.wkf_expr_execute(activity)
                self._state_set(activity, 'complete')

        elif activity['kind'] == WorkflowActivity.KIND_SUBFLOW:

            if self.workitem['state']=='active':

                self._state_set(activity, 'running')
                if activity.get('action', False):
                    id_new = self.wkf_expr_execute(activity)
                    if not id_new:
                        cr.execute('delete from wkf_workitem where id=%s', (self.workitem['id'],))
                        return False
                    assert type(id_new)==type(1) or type(id_new)==type(1L), 'Wrong return value: '+str(id_new)+' '+str(type(id_new))
                    cr.execute('select id from wkf_instance where res_id=%s and wkf_id=%s', (id_new, activity['subflow_id']))
                    id_new = cr.fetchone()[0]
                else:
                    inst = instance.WorkflowInstance(self.session, self.record)
                    id_new = inst.create(activity['subflow_id'])

                cr.execute('update wkf_workitem set subflow_id=%s where id=%s', (id_new, self.workitem['id']))
                self.workitem['subflow_id'] = id_new

            if self.workitem['state']=='running':
                cr.execute("select state from wkf_instance where id=%s", (self.workitem['subflow_id'],))
                state = cr.fetchone()[0]
                if state=='complete':
                    self._state_set(activity, 'complete')

        for instance_id, record, signal_send in signal_todo:
            wi = instance.WorkflowInstance(self.session, record, {'id': instance_id})
            wi.validate(signal_send, force_running=True)

        return result

    def _state_set(self, activity, state):
        self.session.cr.execute('update wkf_workitem set state=%s where id=%s', (state, self.workitem['id']))
        self.workitem['state'] = state
        logger.info('Changed state of work item %s to "%s" in activity %s',
                    self.workitem['id'], state, activity['id'],
                    extra={'ident': (self.session.uid, self.record.model, self.record.id)})

    def _split_test(self, split_mode, signal, stack):
        cr = self.session.cr
        cr.execute('select * from wkf_transition where act_from=%s ORDER BY sequence,id', (self.workitem['act_id'],))
        test = False
        transitions = []
        alltrans = cr.dictfetchall()

        if split_mode in ('XOR', 'OR'):
            for transition in alltrans:
                if self.wkf_expr_check(transition,signal):
                    test = True
                    transitions.append((transition['id'], self.workitem['inst_id']))
                    if split_mode=='XOR':
                        break
        else:
            test = True
            for transition in alltrans:
                if not self.wkf_expr_check(transition, signal):
                    test = False
                    break
                cr.execute('select count(*) from wkf_witm_trans where trans_id=%s and inst_id=%s', (transition['id'], self.workitem['inst_id']))
                if not cr.fetchone()[0]:
                    transitions.append((transition['id'], self.workitem['inst_id']))

        if test and transitions:
            cr.executemany('insert into wkf_witm_trans (trans_id,inst_id) values (%s,%s) except (select trans_id,inst_id from wkf_witm_trans)', transitions)
            cr.execute('delete from wkf_workitem where id=%s', (self.workitem['id'],))
            for t in transitions:
                self._join_test(t[0], t[1], stack)
            return True
        return False

    def _join_test(self, trans_id, inst_id, stack):
        cr = self.session.cr
        cr.execute('select * from wkf_activity where id=(select act_to from wkf_transition where id=%s)', (trans_id,))
        activity = cr.dictfetchone()
        if activity['join_mode']=='XOR':
            WorkflowItem.create(self.session, self.record, activity, inst_id, stack=stack)
            cr.execute('delete from wkf_witm_trans where inst_id=%s and trans_id=%s', (inst_id,trans_id))
        else:
            cr.execute('select id from wkf_transition where act_to=%s ORDER BY sequence,id', (activity['id'],))
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
                WorkflowItem.create(self.session, self.record, activity, inst_id, stack=stack)

    def wkf_expr_eval_expr(self, lines):
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
                env = Environment(self.session, self.record)
                result = eval(line, env, nocopy=True)
        return result

    def wkf_expr_execute_action(self, activity):
        """
        Evaluate the ir.actions.server action specified in the activity.
        """
        context = {
            'active_model': self.record.model,
            'active_id': self.record.id,
            'active_ids': [self.record.id]
        }

        ir_actions_server = openerp.registry(self.session.cr.dbname)['ir.actions.server']
        result = ir_actions_server.run(self.session.cr, self.session.uid, [activity['action_id']], context)

        return result

    def wkf_expr_execute(self, activity):
        """
        Evaluate the action specified in the activity.
        """
        return self.wkf_expr_eval_expr(activity['action'])

    def wkf_expr_check(self, transition, signal):
        """
        Test if a transition can be taken. The transition can be taken if:

        - the signal name matches,
        - the uid is SUPERUSER_ID or the user groups contains the transition's
          group,
        - the condition evaluates to a truish value.
        """
        if transition['signal'] and signal != transition['signal']:
            return False

        if self.session.uid != openerp.SUPERUSER_ID and transition['group_id']:
            registry = openerp.registry(self.session.cr.dbname)
            user_groups = registry['res.users'].read(self.session.cr, self.session.uid, [self.session.uid], ['groups_id'])[0]['groups_id']
            if transition['group_id'] not in user_groups:
                return False

        return self.wkf_expr_eval_expr(transition['condition'])
