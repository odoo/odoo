# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from helpers import Session
from helpers import Record

from openerp.workflow.instance import WorkflowInstance
# import instance


class WorkflowService(object):
    CACHE = {}

    @classmethod
    def clear_cache(cls, dbname):
        cls.CACHE[dbname] = {}

    @classmethod
    def new(cls, cr, uid, model_name, record_id):
        return cls(Session(cr, uid), Record(model_name, record_id))

    def __init__(self, session, record):
        assert isinstance(session, Session)
        assert isinstance(record, Record)

        self.session = session
        self.record = record

        self.cr = self.session.cr

    def write(self):
        self.cr.execute('select id from wkf_instance where res_id=%s and res_type=%s and state=%s',
            (self.record.id or None, self.record.model or None, 'active')
        )
        for (instance_id,) in self.cr.fetchall():
            WorkflowInstance(self.session, self.record, {'id': instance_id}).update()

    def trigger(self):
        self.cr.execute('select instance_id from wkf_triggers where res_id=%s and model=%s', (self.record.id, self.record.model))
        res = self.cr.fetchall()
        for (instance_id,) in res:
            self.cr.execute('select %s,res_type,res_id from wkf_instance where id=%s', (self.session.uid, instance_id,))
            current_uid, current_model_name, current_record_id = self.cr.fetchone()

            current_session = Session(self.session.cr, current_uid)
            current_record = Record(current_model_name, current_record_id)

            WorkflowInstance(current_session, current_record, {'id': instance_id}).update()

    def delete(self):
        WorkflowInstance(self.session, self.record, {}).delete()

    def create(self):
        WorkflowService.CACHE.setdefault(self.cr.dbname, {})

        wkf_ids = WorkflowService.CACHE[self.cr.dbname].get(self.record.model, None)

        if not wkf_ids:
            self.cr.execute('select id from wkf where osv=%s and on_create=True', (self.record.model,))
            wkf_ids = self.cr.fetchall()
            WorkflowService.CACHE[self.cr.dbname][self.record.model] = wkf_ids

        for (wkf_id, ) in wkf_ids:
            WorkflowInstance.create(self.session, self.record, wkf_id)

    def validate(self, signal):
        result = False
        # ids of all active workflow instances for a corresponding resource (id, model_nam)
        self.cr.execute('select id from wkf_instance where res_id=%s and res_type=%s and state=%s', (self.record.id, self.record.model, 'active'))
        # TODO: Refactor the workflow instance object
        for (instance_id,) in self.cr.fetchall():
            wi = WorkflowInstance(self.session, self.record, {'id': instance_id})

            res2 = wi.validate(signal)

            result = result or res2
        return result

    def redirect(self, new_rid):
        # get ids of wkf instances for the old resource (res_id)
        # CHECKME: shouldn't we get only active instances?
        self.cr.execute('select id, wkf_id from wkf_instance where res_id=%s and res_type=%s', (self.record.id, self.record.model))

        for old_inst_id, workflow_id in self.cr.fetchall():
            # first active instance for new resource (new_rid), using same wkf
            self.cr.execute(
                'SELECT id '\
                'FROM wkf_instance '\
                'WHERE res_id=%s AND res_type=%s AND wkf_id=%s AND state=%s',
                (new_rid, self.record.model, workflow_id, 'active'))
            new_id = self.cr.fetchone()
            if new_id:
                # select all workitems which "wait" for the old instance
                self.cr.execute('select id from wkf_workitem where subflow_id=%s', (old_inst_id,))
                for (item_id,) in self.cr.fetchall():
                    # redirect all those workitems to the wkf instance of the new resource
                    self.cr.execute('update wkf_workitem set subflow_id=%s where id=%s', (new_id[0], item_id))
