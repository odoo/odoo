# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2014 Tiny SPRL (<http://tiny.be>).
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

class WorkflowInstance(object):
    def __init__(self, session, record, values):
        assert isinstance(session, Session)
        assert isinstance(record, Record)
        self.session = session
        self.record = record

        if not values:
            values = {}

        assert isinstance(values, dict)
        self.instance = values

    @classmethod
    def create(cls, session, record, workflow_id):
        assert isinstance(session, Session)
        assert isinstance(record, Record)
        assert isinstance(workflow_id, (int, long))

        cr = session.cr
        cr.execute('insert into wkf_instance (res_type,res_id,uid,wkf_id,state) values (%s,%s,%s,%s,%s) RETURNING id', (record.model, record.id, session.uid, workflow_id, 'active'))
        instance_id = cr.fetchone()[0]

        cr.execute('select * from wkf_activity where flow_start=True and wkf_id=%s', (workflow_id,))
        stack = []

        activities = cr.dictfetchall()
        for activity in activities:
            WorkflowItem.create(session, record, activity, instance_id, stack)

        cr.execute('SELECT * FROM wkf_instance WHERE id = %s', (instance_id,))
        values = cr.dictfetchone()
        wi = WorkflowInstance(session, record, values)
        wi.update()

        return wi

    def delete(self):
        self.session.cr.execute('delete from wkf_instance where res_id=%s and res_type=%s', (self.record.id, self.record.model))

    def validate(self, signal, force_running=False):
        assert isinstance(signal, basestring)
        assert isinstance(force_running, bool)

        cr = self.session.cr
        cr.execute("select * from wkf_workitem where inst_id=%s", (self.instance['id'],))
        stack = []
        for work_item_values in cr.dictfetchall():
            wi = WorkflowItem(self.session, self.record, work_item_values)
            wi.process(signal=signal, force_running=force_running, stack=stack)
            # An action is returned
        self._update_end()
        return stack and stack[0] or False

    def update(self):
        cr = self.session.cr

        cr.execute("select * from wkf_workitem where inst_id=%s", (self.instance['id'],))
        for work_item_values in cr.dictfetchall():
            stack = []
            WorkflowItem(self.session, self.record, work_item_values).process(stack=stack)
        return self._update_end()

    def _update_end(self):
        cr = self.session.cr
        instance_id = self.instance['id']
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
                    WorkflowInstance(self.session, cur_record, {'id':cur_instance_id}).validate('subflow.%s' % act_name[0])

        return ok





def create(session, record, workflow_id):
    return WorkflowInstance(session, record).create(workflow_id)

def delete(session, record):
    return WorkflowInstance(session, record).delete()

def validate(session, record, instance_id, signal, force_running=False):
    return WorkflowInstance(session, record).validate(instance_id, signal, force_running)

def update(session, record, instance_id):
    return WorkflowInstance(session, record).update(instance_id)

def _update_end(session, record, instance_id):
    return WorkflowInstance(session, record)._update_end(instance_id)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

