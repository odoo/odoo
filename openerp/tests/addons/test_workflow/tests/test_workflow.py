# -*- coding: utf-8 -*-
import openerp
from openerp import SUPERUSER_ID
from openerp.tests import common


class test_workflows(common.TransactionCase):

    def check_activities(self, model_name, i, names):
        """ Check that the record i has workitems in the given activity names.
        """
        instance = self.registry('workflow.instance')
        workitem = self.registry('workflow.workitem')

        # Given the workflow instance associated to the record ...
        instance_id = instance.search(
            self.cr, SUPERUSER_ID,
            [('res_type', '=', model_name), ('res_id', '=', i)])
        self.assertTrue( instance_id, 'A workflow instance is expected.')

        # ... get all its workitems ...
        workitem_ids = workitem.search(
            self.cr, SUPERUSER_ID,
            [('inst_id', '=', instance_id[0])])
        self.assertTrue(
            workitem_ids,
            'The workflow instance should have workitems.')

        # ... and check the activity the are in against the provided names.
        workitem_records = workitem.browse(
            self.cr, SUPERUSER_ID, workitem_ids)
        self.assertEqual(
            sorted([item.act_id.name for item in workitem_records]),
            sorted(names))

    def check_value(self, model_name, i, value):
        """ Check that the record i has the given value.
        """
        model = self.registry(model_name)
        record = model.read(self.cr, SUPERUSER_ID, [i], ['value'])[0]
        self.assertEqual(record['value'], value)

    def test_workflow(self):
        model = self.registry('test.workflow.model')
        trigger = self.registry('test.workflow.trigger')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['a'])

        # a -> b is just a signal.
        model.signal_workflow(self.cr, SUPERUSER_ID, [i], 'a-b')
        self.check_activities(model._name, i, ['b'])

        # b -> c is a trigger (which is False),
        # so we remain in the b activity.
        model.trigger(self.cr, SUPERUSER_ID)
        self.check_activities(model._name, i, ['b'])

        # b -> c is a trigger (which is set to True).
        # so we go in c when the trigger is called.
        trigger.write(self.cr, SUPERUSER_ID, [1], {'value': True})
        model.trigger(self.cr, SUPERUSER_ID)
        self.check_activities(model._name, i, ['c'])

        self.assertEqual(
            True,
            True)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_a(self):
        model = self.registry('test.workflow.model.a')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['a'])
        self.check_value(model._name, i, 0)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_b(self):
        model = self.registry('test.workflow.model.b')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['a'])
        self.check_value(model._name, i, 1)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_c(self):
        model = self.registry('test.workflow.model.c')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['a'])
        self.check_value(model._name, i, 0)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_d(self):
        model = self.registry('test.workflow.model.d')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['a'])
        self.check_value(model._name, i, 1)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_e(self):
        model = self.registry('test.workflow.model.e')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['b'])
        self.check_value(model._name, i, 2)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_f(self):
        model = self.registry('test.workflow.model.f')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['a'])
        self.check_value(model._name, i, 1)

        model.signal_workflow(self.cr, SUPERUSER_ID, [i], 'a-b')
        self.check_activities(model._name, i, ['b'])
        self.check_value(model._name, i, 2)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_g(self):
        model = self.registry('test.workflow.model.g')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['a'])
        self.check_value(model._name, i, 1)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_h(self):
        model = self.registry('test.workflow.model.h')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['b', 'c'])
        self.check_value(model._name, i, 2)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_i(self):
        model = self.registry('test.workflow.model.i')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['b'])
        self.check_value(model._name, i, 2)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_j(self):
        model = self.registry('test.workflow.model.j')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['a'])
        self.check_value(model._name, i, 1)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_k(self):
        model = self.registry('test.workflow.model.k')

        i = model.create(self.cr, SUPERUSER_ID, {})
        # Non-determinisitic: can be b or c
        # self.check_activities(model._name, i, ['b'])
        # self.check_activities(model._name, i, ['c'])
        self.check_value(model._name, i, 2)

        model.unlink(self.cr, SUPERUSER_ID, [i])

    def test_workflow_l(self):
        model = self.registry('test.workflow.model.l')

        i = model.create(self.cr, SUPERUSER_ID, {})
        self.check_activities(model._name, i, ['c', 'c', 'd'])
        self.check_value(model._name, i, 3)

        model.unlink(self.cr, SUPERUSER_ID, [i])
