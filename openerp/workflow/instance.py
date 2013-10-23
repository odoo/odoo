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
import workitem
from openerp.workflow.helpers import Session
from openerp.workflow.helpers import Record
from openerp.workflow.workitem import WorkflowItem

def create(session, record, workflow_id):
    assert isinstance(session, Session)
    assert isinstance(record, Record)
    assert isinstance(workflow_id, (int, long))

    cr = session.cr
    cr.execute('insert into wkf_instance (res_type,res_id,uid,wkf_id) values (%s,%s,%s,%s) RETURNING id', (record.model, record.id, session.uid, workflow_id))
    instance_id = cr.fetchone()[0]
    cr.execute('select * from wkf_activity where flow_start=True and wkf_id=%s', (workflow_id,))
    activities = cr.dictfetchall()
    stack = []
    WorkflowItem(session, record).create(activities, instance_id, stack)
    update(session, record, instance_id)
    return instance_id

def delete(session, record):
    assert isinstance(session, Session)
    assert isinstance(record, Record)

    session.cr.execute('delete from wkf_instance where res_id=%s and res_type=%s', (record.id, record.model))

def validate(session, record, instance_id, signal, force_running=False):
    assert isinstance(session, Session)
    assert isinstance(record, Record)
    assert isinstance(instance_id, (long, int))
    assert isinstance(signal, basestring)
    assert isinstance(force_running, bool)

    cr = session.cr
    cr.execute("select * from wkf_workitem where inst_id=%s", (instance_id,))
    stack = []
    wi = WorkflowItem(session, record)
    for work_item in cr.dictfetchall():
        # stack = []
        wi.process(work_item, signal, force_running, stack=stack)
        # An action is returned
    _update_end(session, record, instance_id)
    return stack and stack[0] or False

def update(session, record, instance_id):
    assert isinstance(session, Session)
    assert isinstance(record, Record)
    assert isinstance(instance_id, (long, int))

    cr = session.cr
    cr.execute("select * from wkf_workitem where inst_id=%s", (instance_id,))
    wi = WorkflowItem(session, record)

    for work_item in cr.dictfetchall():
        stack = []
        wi.process(work_item, stack=stack)
    return _update_end(session, record, instance_id)

def _update_end(session, record, instance_id):
    assert isinstance(session, Session)
    assert isinstance(record, Record)
    assert isinstance(instance_id, (long, int))

    cr = session.cr
    cr.execute('select wkf_id from wkf_instance where id=%s', (instance_id,))
    wkf_id = cr.fetchone()[0]
    cr.execute('select state,flow_stop from wkf_workitem w left join wkf_activity a on (a.id=w.act_id) where w.inst_id=%s', (instance_id,))
    ok=True
    for r in cr.fetchall():
        if (r[0]<>'complete') or not r[1]:
            ok=False
            break
    if ok:
        cr.execute('select distinct a.name from wkf_activity a left join wkf_workitem w on (a.id=w.act_id) where w.inst_id=%s', (instance_id,))
        act_names = cr.fetchall()
        cr.execute("update wkf_instance set state='complete' where id=%s", (instance_id,))
        cr.execute("update wkf_workitem set state='complete' where subflow_id=%s", (instance_id,))
        cr.execute("select i.id,w.osv,i.res_id from wkf_instance i left join wkf w on (i.wkf_id=w.id) where i.id IN (select inst_id from wkf_workitem where subflow_id=%s)", (instance_id,))
        for cur_instance_id, cur_model_name, cur_record_id in cr.fetchall():
            cur_record = Record(cur_model_name, cur_record_id)
            for act_name in act_names:
                validate(session, cur_record, cur_instance_id, 'subflow.%s' % act_name[0])

    return ok


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

