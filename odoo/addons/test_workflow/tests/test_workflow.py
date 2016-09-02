# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class test_workflows(common.TransactionCase):

    def check_activities(self, record, names):
        """ Check that the record has workitems in the given activity names.
        """
        Instance = self.env['workflow.instance']
        Workitem = self.env['workflow.workitem']

        # Given the workflow instance associated to the record ...
        instance = Instance.search([('res_type', '=', record._name), ('res_id', '=', record.id)])
        self.assertTrue(instance, 'A workflow instance is expected.')

        # ... get all its workitems ...
        workitems = Workitem.search([('inst_id', '=', instance.id)])
        self.assertTrue(workitems, 'The workflow instance should have workitems.')

        # ... and check the activity the are in against the provided names.
        self.assertEqual(
            sorted([item.act_id.name for item in workitems]),
            sorted(names))

    def check_value(self, record, value):
        """ Check that the record has the given value.
        """
        self.assertEqual(record.value, value)

    def test_workflow(self):
        model = self.env['test.workflow.model']
        trigger = self.env['test.workflow.trigger']

        record = model.create({})
        self.check_activities(record, ['a'])

        # a -> b is just a signal.
        record.signal_workflow('a-b')
        self.check_activities(record, ['b'])

        # b -> c is a trigger (which is False),
        # so we remain in the b activity.
        record.trigger()
        self.check_activities(record, ['b'])

        # b -> c is a trigger (which is set to True).
        # so we go in c when the trigger is called.
        trigger.browse(1).write({'value': True})
        record.trigger()
        self.check_activities(record, ['c'])

        self.assertEqual(True, True)

    def test_workflow_a(self):
        record = self.env['test.workflow.model.a'].create({})
        self.check_activities(record, ['a'])
        self.check_value(record, 0)

    def test_workflow_b(self):
        record = self.env['test.workflow.model.b'].create({})
        self.check_activities(record, ['a'])
        self.check_value(record, 1)

    def test_workflow_c(self):
        record = self.env['test.workflow.model.c'].create({})
        self.check_activities(record, ['a'])
        self.check_value(record, 0)

    def test_workflow_d(self):
        record = self.env['test.workflow.model.d'].create({})
        self.check_activities(record, ['a'])
        self.check_value(record, 1)

    def test_workflow_e(self):
        record = self.env['test.workflow.model.e'].create({})
        self.check_activities(record, ['b'])
        self.check_value(record, 2)

    def test_workflow_f(self):
        record = self.env['test.workflow.model.f'].create({})
        self.check_activities(record, ['a'])
        self.check_value(record, 1)

        record.signal_workflow('a-b')
        self.check_activities(record, ['b'])
        self.check_value(record, 2)

    def test_workflow_g(self):
        record = self.env['test.workflow.model.g'].create({})
        self.check_activities(record, ['a'])
        self.check_value(record, 1)

    def test_workflow_h(self):
        record = self.env['test.workflow.model.h'].create({})
        self.check_activities(record, ['b', 'c'])
        self.check_value(record, 2)

    def test_workflow_i(self):
        record = self.env['test.workflow.model.i'].create({})
        self.check_activities(record, ['b'])
        self.check_value(record, 2)

    def test_workflow_j(self):
        record = self.env['test.workflow.model.j'].create({})
        self.check_activities(record, ['a'])
        self.check_value(record, 1)

    def test_workflow_k(self):
        record = self.env['test.workflow.model.k'].create({})
        # Non-determinisitic: can be b or c
        # self.check_activities(record, ['b'])
        # self.check_activities(record, ['c'])
        self.check_value(record, 2)

    def test_workflow_l(self):
        record = self.env['test.workflow.model.l'].create({})
        self.check_activities(record, ['c', 'c', 'd'])
        self.check_value(record, 3)
