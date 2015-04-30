# -*- coding: utf-8 -*-
from openerp.tests import common


class TestBaseActionRule(common.TransactionCase):

    def setUp(self):
        """*****setUp*****"""
        super(TestBaseActionRule, self).setUp()
        self.Demo = self.env.ref('base.user_demo')
        self.Model = self.env['base.action.rule.lead.test']
        self.BaseActionRule = self.env['base.action.rule']

    def create_filter_done(self):
        FilterPool = self.env['ir.filters']
        return FilterPool.create({
            'name': "Lead is in done state",
            'is_default': False,
            'model_id': 'base.action.rule.lead.test',
            'domain': "[('state','=','done')]",
        })

    def create_filter_draft(self):
        FilterPool = self.env['ir.filters']
        return FilterPool.create({
            'name': "Lead is in draft state",
            'is_default': False,
            'model_id': "base.action.rule.lead.test",
            'domain': "[('state','=','draft')]",
        })

    def create_lead_test_1(self):
        """
            Create a new LeadTest
        """
        return self.Model.create({
            'name': "Lead Test 1",
            'user_id': self.uid,
        })

    def create_rule(self, kind, filter_id=False, filter_pre_id=False):
        """
            The "Rule 1" says that when a lead goes to the 'draft' state, the responsible for that lead changes to user "demo"
        """
        return self.BaseActionRule.create({
            'name': "Rule 1",
            'model_id': self.env['ir.model'].search([('model', '=', 'base.action.rule.lead.test')]).ids[0],
            'kind': kind,
            'filter_pre_id': filter_pre_id,
            'filter_id': filter_id,
            'act_user_id': self.Demo.id,
        })

    def delete_rules(self):
        """ delete all the rules on model 'base.action.rule.lead.test' """
        return self.BaseActionRule.search([('model', '=', self.Model._name)]).unlink()

    def test_00_check_to_state_draft_pre(self):
        """
        Check that a new record (with state = draft) doesn't change its responsible when there is a precondition filter which check that the state is draft.
        """
        filter_draft = self.create_filter_draft()
        self.create_rule('on_write', filter_pre_id=filter_draft.id)
        new_lead = self.create_lead_test_1()
        self.assertEquals(new_lead.state, 'draft')
        self.assertEquals(new_lead.user_id.id, self.uid)
        self.delete_rules()

    def test_01_check_to_state_draft_post(self):
        """
        Check that a new record changes its responsible when there is a postcondition filter which check that the state is draft.
        """
        filter_draft = self.create_filter_draft()
        self.create_rule('on_create')
        new_lead = self.create_lead_test_1()
        self.assertEquals(new_lead.state, 'draft')
        self.assertEquals(new_lead.user_id.id, self.Demo.id)
        self.delete_rules()

    def test_02_check_from_draft_to_done_with_steps(self):
        """
        A new record will be created and will goes from draft to done state via the other states (open, pending and cancel)
        We will create a rule that says in precondition that the record must be in the "draft" state while a postcondition filter says
        that the record will be done. If the state goes from 'draft' to 'done' the responsible will change. If those two conditions aren't
        verified, the responsible will stay the same
        The responsible in that test will never change
        """
        filter_draft = self.create_filter_draft()
        filter_done = self.create_filter_done()
        self.create_rule('on_write', filter_pre_id=filter_draft.id, filter_id=filter_done.id)
        new_lead = self.create_lead_test_1()
        self.assertEquals(new_lead.state, 'draft')
        self.assertEquals(new_lead.user_id.id, self.uid)
        """ change the state of new_lead to open and check that responsible doen't change"""
        new_lead.write({'state': 'open'})
        self.assertEquals(new_lead.state, 'open')
        self.assertEquals(new_lead.user_id.id, self.uid)
        """ change the state of new_lead to pending and check that responsible doen't change"""
        new_lead.write({'state': 'pending'})
        self.assertEquals(new_lead.state, 'pending')
        self.assertEquals(new_lead.user_id.id, self.uid)
        """ change the state of new_lead to cancel and check that responsible doen't change"""
        new_lead.write({'state': 'cancel'})
        self.assertEquals(new_lead.state, 'cancel')
        self.assertEquals(new_lead.user_id.id, self.uid)
        """ change the state of new_lead to done and check that responsible doen't change """
        new_lead.write({'state': 'done'})
        self.assertEquals(new_lead.state, 'done')
        self.assertEquals(new_lead.user_id.id, self.uid)
        self.delete_rules()

    def test_02_check_from_draft_to_done_without_steps(self):
        """
        A new record will be created and will goes from draft to done in one operation
        We will create a rule that says in precondition that the record must be in the "draft" state while a postcondition filter says
        that the record will be done. If the state goes from 'draft' to 'done' the responsible will change. If those two conditions aren't
        verified, the responsible will stay the same
        The responsible in that test will change to user "demo"
        """
        filter_draft = self.create_filter_draft()
        filter_done = self.create_filter_done()
        self.create_rule('on_write', filter_pre_id=filter_draft.id, filter_id=filter_done.id)
        new_lead = self.create_lead_test_1()
        self.assertEquals(new_lead.state, 'draft')
        self.assertEquals(new_lead.user_id.id, self.uid)
        """ change the state of new_lead to done and check that responsible change to Demo_user"""
        new_lead.write({'state': 'done'})
        self.assertEquals(new_lead.state, 'done')
        self.assertEquals(new_lead.user_id.id, self.Demo.id)
        self.delete_rules()
