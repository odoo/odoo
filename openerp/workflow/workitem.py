# -*- coding: utf-8 -*-
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

import instance

import wkf_expr
import wkf_logs

def create(cr, act_datas, inst_id, ident, stack):
    for act in act_datas:
        cr.execute("select nextval('wkf_workitem_id_seq')")
        id_new = cr.fetchone()[0]
        cr.execute("insert into wkf_workitem (id,act_id,inst_id,state) values (%s,%s,%s,'active')", (id_new, act['id'], inst_id))
        cr.execute('select * from wkf_workitem where id=%s',(id_new,))
        res = cr.dictfetchone()
        wkf_logs.log(cr,ident,act['id'],'active')
        process(cr, res, ident, stack=stack)

def process(cr, workitem, ident, signal=None, force_running=False, stack=None):
    if stack is None:
        raise 'Error !!!'
    result = True
    cr.execute('select * from wkf_activity where id=%s', (workitem['act_id'],))
    activity = cr.dictfetchone()

    triggers = False
    if workitem['state']=='active':
        triggers = True
        result = _execute(cr, workitem, activity, ident, stack)
        if not result:
            return False

    if workitem['state']=='running':
        pass

    if workitem['state']=='complete' or force_running:
        ok = _split_test(cr, workitem, activity['split_mode'], ident, signal, stack)
        triggers = triggers and not ok

    if triggers:
        cr.execute('select * from wkf_transition where act_from=%s', (workitem['act_id'],))
        alltrans = cr.dictfetchall()
        for trans in alltrans:
            if trans['trigger_model']:
                ids = wkf_expr._eval_expr(cr,ident,workitem,trans['trigger_expr_id'])
                for res_id in ids:
                    cr.execute('select nextval(\'wkf_triggers_id_seq\')')
                    id =cr.fetchone()[0]
                    cr.execute('insert into wkf_triggers (model,res_id,instance_id,workitem_id,id) values (%s,%s,%s,%s,%s)', (trans['trigger_model'],res_id,workitem['inst_id'], workitem['id'], id))

    return result


# ---------------------- PRIVATE FUNCS --------------------------------

def _state_set(cr, workitem, activity, state, ident):
    cr.execute('update wkf_workitem set state=%s where id=%s', (state,workitem['id']))
    workitem['state'] = state
    wkf_logs.log(cr,ident,activity['id'],state)

def _execute(cr, workitem, activity, ident, stack):
    result = True
    #
    # send a signal to parent workflow (signal: subflow.signal_name)
    #
    signal_todo = []
    if (workitem['state']=='active') and activity['signal_send']:
        cr.execute("select i.id,w.osv,i.res_id from wkf_instance i left join wkf w on (i.wkf_id=w.id) where i.id IN (select inst_id from wkf_workitem where subflow_id=%s)", (workitem['inst_id'],))
        for i in cr.fetchall():
            signal_todo.append((i[0], (ident[0],i[1],i[2]), activity['signal_send']))

    if activity['kind']=='dummy':
        if workitem['state']=='active':
            _state_set(cr, workitem, activity, 'complete', ident)
            if activity['action_id']:
                res2 = wkf_expr.execute_action(cr, ident, workitem, activity)
                if res2:
                    stack.append(res2)
                    result=res2
    elif activity['kind']=='function':
        if workitem['state']=='active':
            _state_set(cr, workitem, activity, 'running', ident)
            returned_action = wkf_expr.execute(cr, ident, workitem, activity)
            if type(returned_action) in (dict,):
                stack.append(returned_action)
            if activity['action_id']:
                res2 = wkf_expr.execute_action(cr, ident, workitem, activity)
                # A client action has been returned
                if res2:
                    stack.append(res2)
                    result=res2
            _state_set(cr, workitem, activity, 'complete', ident)
    elif activity['kind']=='stopall':
        if workitem['state']=='active':
            _state_set(cr, workitem, activity, 'running', ident)
            cr.execute('delete from wkf_workitem where inst_id=%s and id<>%s', (workitem['inst_id'], workitem['id']))
            if activity['action']:
                wkf_expr.execute(cr, ident, workitem, activity)
            _state_set(cr, workitem, activity, 'complete', ident)
    elif activity['kind']=='subflow':
        if workitem['state']=='active':
            _state_set(cr, workitem, activity, 'running', ident)
            if activity.get('action', False):
                id_new = wkf_expr.execute(cr, ident, workitem, activity)
                if not id_new:
                    cr.execute('delete from wkf_workitem where id=%s', (workitem['id'],))
                    return False
                assert type(id_new)==type(1) or type(id_new)==type(1L), 'Wrong return value: '+str(id_new)+' '+str(type(id_new))
                cr.execute('select id from wkf_instance where res_id=%s and wkf_id=%s', (id_new,activity['subflow_id']))
                id_new = cr.fetchone()[0]
            else:
                id_new = instance.create(cr, ident, activity['subflow_id'])
            cr.execute('update wkf_workitem set subflow_id=%s where id=%s', (id_new, workitem['id']))
            workitem['subflow_id'] = id_new
        if workitem['state']=='running':
            cr.execute("select state from wkf_instance where id=%s", (workitem['subflow_id'],))
            state= cr.fetchone()[0]
            if state=='complete':
                _state_set(cr, workitem, activity, 'complete', ident)
    for t in signal_todo:
        instance.validate(cr, t[0], t[1], t[2], force_running=True)

    return result

def _split_test(cr, workitem, split_mode, ident, signal=None, stack=None):
    if stack is None:
        raise 'Error !!!'
    cr.execute('select * from wkf_transition where act_from=%s', (workitem['act_id'],))
    test = False
    transitions = []
    alltrans = cr.dictfetchall()
    if split_mode=='XOR' or split_mode=='OR':
        for transition in alltrans:
            if wkf_expr.check(cr, workitem, ident, transition,signal):
                test = True
                transitions.append((transition['id'], workitem['inst_id']))
                if split_mode=='XOR':
                    break
    else:
        test = True
        for transition in alltrans:
            if not wkf_expr.check(cr, workitem, ident, transition,signal):
                test = False
                break
            cr.execute('select count(*) from wkf_witm_trans where trans_id=%s and inst_id=%s', (transition['id'], workitem['inst_id']))
            if not cr.fetchone()[0]:
                transitions.append((transition['id'], workitem['inst_id']))
    if test and len(transitions):
        cr.executemany('insert into wkf_witm_trans (trans_id,inst_id) values (%s,%s)', transitions)
        cr.execute('delete from wkf_workitem where id=%s', (workitem['id'],))
        for t in transitions:
            _join_test(cr, t[0], t[1], ident, stack)
        return True
    return False

def _join_test(cr, trans_id, inst_id, ident, stack):
    cr.execute('select * from wkf_activity where id=(select act_to from wkf_transition where id=%s)', (trans_id,))
    activity = cr.dictfetchone()
    if activity['join_mode']=='XOR':
        create(cr,[activity], inst_id, ident, stack)
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
            create(cr, [activity], inst_id, ident, stack)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

