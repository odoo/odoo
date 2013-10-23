
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import wkf_expr
from helpers import Session
from helpers import Record

logger = logging.getLogger(__name__)

def create(session, record, activities, instance_id, stack):
    assert isinstance(session, Session)
    assert isinstance(record, Record)
    assert isinstance(activities, list)
    assert isinstance(instance_id, (long, int))
    assert isinstance(stack, list)
    cr = session.cr

    ident = session.uid, record.model, record.id
    for activity in activities:
        cr.execute("select nextval('wkf_workitem_id_seq')")
        id_new = cr.fetchone()[0]
        cr.execute("insert into wkf_workitem (id,act_id,inst_id,state) values (%s,%s,%s,'active')", (id_new, activity['id'], instance_id))
        cr.execute('select * from wkf_workitem where id=%s',(id_new,))
        work_item = cr.dictfetchone()
        logger.info('Created workflow item in activity %s',
                    activity['id'],
                    extra={'ident': (session.uid, record.model, record.id)})

        process(session, record, work_item, stack=stack)

def process(session, record, workitem, signal=None, force_running=False, stack=None):
    assert isinstance(session, Session)
    assert isinstance(record, Record)
    assert isinstance(force_running, bool)

    assert stack is not None

    cr = session.cr

    cr.execute('select * from wkf_activity where id=%s', (workitem['act_id'],))
    activity = cr.dictfetchone()

    triggers = False
    if workitem['state'] == 'active':
        triggers = True
        if not _execute(session, record, workitem, activity, stack):
            return False

    if force_running or workitem['state'] == 'complete':
        ok = _split_test(session, record, workitem, activity['split_mode'], signal, stack)
        triggers = triggers and not ok

    if triggers:
        cr.execute('select * from wkf_transition where act_from=%s', (workitem['act_id'],))
        for trans in cr.dictfetchall():
            if trans['trigger_model']:
                ids = wkf_expr._eval_expr(session, record, workitem, trans['trigger_expr_id'])
                for res_id in ids:
                    cr.execute('select nextval(\'wkf_triggers_id_seq\')')
                    id =cr.fetchone()[0]
                    cr.execute('insert into wkf_triggers (model,res_id,instance_id,workitem_id,id) values (%s,%s,%s,%s,%s)', (trans['trigger_model'],res_id,workitem['inst_id'], workitem['id'], id))

    return True


# ---------------------- PRIVATE FUNCS --------------------------------

# def new_state_set(session, record, workitem, activity, state):

def _state_set(session, record, workitem, activity, state):
    session.cr.execute('update wkf_workitem set state=%s where id=%s', (state, workitem['id']))
    workitem['state'] = state
    logger.info('Changed state of work item %s to "%s" in activity %s',
                workitem['id'], state, activity['id'],
                extra={'ident': (session.uid, record.model, record.id)})

def _execute(session, record, workitem, activity, stack):
    result = True
    #
    # send a signal to parent workflow (signal: subflow.signal_name)
    #
    cr = session.cr
    ident = (session.uid, record.model, record.id)
    signal_todo = []
    if (workitem['state']=='active') and activity['signal_send']:
        cr.execute("select i.id,w.osv,i.res_id from wkf_instance i left join wkf w on (i.wkf_id=w.id) where i.id IN (select inst_id from wkf_workitem where subflow_id=%s)", (workitem['inst_id'],))
        for instance_id, model_name, record_id in cr.fetchall():
            record = Record(model_name, record_id)
            signal_todo.append((instance_id, record, activity['signal_send']))

    if activity['kind']=='dummy':
        if workitem['state']=='active':
            _state_set(session, record, workitem, activity, 'complete')
            if activity['action_id']:
                res2 = wkf_expr.execute_action(cr, ident, workitem, activity)
                if res2:
                    stack.append(res2)
                    result=res2
    elif activity['kind']=='function':
        if workitem['state']=='active':
            _state_set(session, record, workitem, activity, 'running')
            returned_action = wkf_expr.execute(session, record, workitem, activity)
            if type(returned_action) in (dict,):
                stack.append(returned_action)
            if activity['action_id']:
                res2 = wkf_expr.execute_action(session, record, workitem, activity)
                # A client action has been returned
                if res2:
                    stack.append(res2)
                    result=res2
            _state_set(session, record, workitem, activity, 'complete')
    elif activity['kind']=='stopall':
        if workitem['state']=='active':
            _state_set(session, record, workitem, activity, 'running')
            cr.execute('delete from wkf_workitem where inst_id=%s and id<>%s', (workitem['inst_id'], workitem['id']))
            if activity['action']:
                wkf_expr.execute(session, record, workitem, activity)
            _state_set(session, record, workitem, activity, 'complete')
    elif activity['kind']=='subflow':
        if workitem['state']=='active':
            _state_set(session, record, workitem, activity, 'running')
            if activity.get('action', False):
                id_new = wkf_expr.execute(session, record, workitem, activity)
                if not id_new:
                    cr.execute('delete from wkf_workitem where id=%s', (workitem['id'],))
                    return False
                assert type(id_new)==type(1) or type(id_new)==type(1L), 'Wrong return value: '+str(id_new)+' '+str(type(id_new))
                cr.execute('select id from wkf_instance where res_id=%s and wkf_id=%s', (id_new,activity['subflow_id']))
                id_new = cr.fetchone()[0]
            else:
                id_new = instance.create(session, record, activity['subflow_id'])
            cr.execute('update wkf_workitem set subflow_id=%s where id=%s', (id_new, workitem['id']))
            workitem['subflow_id'] = id_new
        if workitem['state']=='running':
            cr.execute("select state from wkf_instance where id=%s", (workitem['subflow_id'],))
            state= cr.fetchone()[0]
            if state=='complete':
                _state_set(session, record, workitem, activity, 'complete')

    for instance_id, record, signal_send in signal_todo:
        instance.validate(session, record, signal_send, force_running=True)

    return result

def _split_test(session, record, workitem, split_mode, signal, stack):
    cr = session.cr
    cr.execute('select * from wkf_transition where act_from=%s', (workitem['act_id'],))
    test = False
    transitions = []
    alltrans = cr.dictfetchall()
    if split_mode=='XOR' or split_mode=='OR':
        for transition in alltrans:
            if wkf_expr.check(session, record, workitem, transition,signal):
                test = True
                transitions.append((transition['id'], workitem['inst_id']))
                if split_mode=='XOR':
                    break
    else:
        test = True
        for transition in alltrans:
            if not wkf_expr.check(session, record, workitem, transition,signal):
                test = False
                break
            cr.execute('select count(*) from wkf_witm_trans where trans_id=%s and inst_id=%s', (transition['id'], workitem['inst_id']))
            if not cr.fetchone()[0]:
                transitions.append((transition['id'], workitem['inst_id']))
    if test and len(transitions):
        cr.executemany('insert into wkf_witm_trans (trans_id,inst_id) values (%s,%s)', transitions)
        cr.execute('delete from wkf_workitem where id=%s', (workitem['id'],))
        for t in transitions:
            _join_test(session, record, t[0], t[1], stack)
        return True
    return False

def _join_test(session, record, trans_id, inst_id, stack):
    # cr, trans_id, inst_id, ident, stack):
    cr = session.cr
    cr.execute('select * from wkf_activity where id=(select act_to from wkf_transition where id=%s)', (trans_id,))
    activity = cr.dictfetchone()
    if activity['join_mode']=='XOR':
        create(session, record, [activity], inst_id, stack)
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
            create(session, record, [activity], inst_id, stack)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

