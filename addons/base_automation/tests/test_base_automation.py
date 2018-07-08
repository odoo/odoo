# # -*- coding: utf-8 -*-
# # Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


@common.tagged('post_install','-at_install')
class base_automation_test(common.TransactionCase):

    def setUp(self):
        super(base_automation_test, self).setUp()
        self.user_admin = self.env.ref('base.user_root')
        self.user_demo = self.env.ref('base.user_demo')

    def create_lead(self, **kwargs):
        vals = {
            'name': "Lead Test",
            'user_id': self.user_admin.id,
        }
        vals.update(kwargs)
        return self.env['base.automation.lead.test'].create(vals)

    def test_00_check_to_state_open_pre(self):
        """
        Check that a new record (with state = open) doesn't change its responsible
        when there is a precondition filter which check that the state is open.
        """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open')
        self.assertEqual(lead.user_id, self.user_admin, "Responsible should not change on creation of Lead with state 'open'.")

    def test_01_check_to_state_draft_post(self):
        """
        Check that a new record changes its responsible when there is a postcondition
        filter which check that the state is draft.
        """
        lead = self.create_lead()
        self.assertEqual(lead.state, 'draft', "Lead state should be 'draft'")
        self.assertEqual(lead.user_id, self.user_demo, "Responsible should be change on creation of Lead with state 'draft'.")

    def test_02_check_from_draft_to_done_with_steps(self):
        """
        A new record is created and goes from states 'open' to 'done' via the
        other states (open, pending and cancel). We have a rule with:
         - precondition: the record is in "open"
         - postcondition: that the record is "done".
        If the state goes from 'open' to 'done' the responsible is changed.
        If those two conditions aren't verified, the responsible remains the same.
        """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open', "Lead state should be 'open'")
        self.assertEqual(lead.user_id, self.user_admin, "Responsible should not change on creation of Lead with state 'open'.")
        # change state to pending and check that responsible has not changed
        lead.write({'state': 'pending'})
        self.assertEqual(lead.state, 'pending', "Lead state should be 'pending'")
        self.assertEqual(lead.user_id, self.user_admin, "Responsible should not change on creation of Lead with state from 'draft' to 'open'.")
        # change state to done and check that responsible has not changed
        lead.write({'state': 'done'})
        self.assertEqual(lead.state, 'done', "Lead state should be 'done'")
        self.assertEqual(lead.user_id, self.user_admin, "Responsible should not chang on creation of Lead with state from 'pending' to 'done'.")

    def test_03_check_from_draft_to_done_without_steps(self):
        """
        A new record is created and goes from states 'open' to 'done' via the
        other states (open, pending and cancel). We have a rule with:
         - precondition: the record is in "open"
         - postcondition: that the record is "done".
        If the state goes from 'open' to 'done' the responsible is changed.
        If those two conditions aren't verified, the responsible remains the same.
        """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open', "Lead state should be 'open'")
        self.assertEqual(lead.user_id, self.user_admin, "Responsible should not change on creation of Lead with state 'open'.")
        # change state to done and check that responsible has changed
        lead.write({'state': 'done'})
        self.assertEqual(lead.state, 'done', "Lead state should be 'done'")
        self.assertEqual(lead.user_id, self.user_demo, "Responsible should be change on write of Lead with state from 'open' to 'done'.")

    def test_10_recomputed_field(self):
        """
        Check that a rule is executed whenever a field is recomputed after a
        change on another model.
        """
        partner = self.env.ref('base.res_partner_1')
        partner.write({'customer': False})
        lead = self.create_lead(state='open', partner_id=partner.id)
        self.assertFalse(lead.customer, "Customer field should updated to False")
        self.assertEqual(lead.user_id, self.user_admin, "Responsible should not change on creation of Lead with state from 'draft' to 'open'.")
        # change partner, recompute on lead should trigger the rule
        partner.write({'customer': True})
        self.assertTrue(lead.customer, "Customer field should updated to True")
        self.assertEqual(lead.user_id, self.user_demo, "Responsible should be change on write of Lead when Customer becomes True.")

    def test_11_recomputed_field(self):
        """
        Check that a rule is executed whenever a field is recomputed and the
        context contains the target field
        """
        partner = self.env.ref('base.res_partner_1')
        lead = self.create_lead(state='draft', partner_id=partner.id)
        self.assertFalse(lead.deadline, 'There should not be a deadline defined')
        # change priority and user; this triggers deadline recomputation, and
        # the server action should set the boolean field to True
        lead.write({'priority': True, 'user_id': self.user_admin.id})
        self.assertTrue(lead.deadline, 'Deadline should be defined')
        self.assertTrue(lead.is_assigned_to_admin, 'Lead should be assigned to admin')

    def test_12_recursive(self):
        """ Check that a rule is executed recursively by a secondary change. """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open')
        self.assertEqual(lead.user_id, self.user_admin)
        # change partner; this should trigger the rule that modifies the state
        partner = self.env.ref('base.res_partner_1')
        lead.write({'partner_id': partner.id})
        self.assertEqual(lead.state, 'draft')

    def test_20_direct_line(self):
        """
        Check that a rule is executed after creating a line record.
        """
        line = self.env['base.automation.line.test'].create({'name': "Line"})
        self.assertEqual(line.user_id, self.user_demo)

    def test_20_indirect_line(self):
        """
        Check that creating a lead with a line executes rules on both records.
        """
        lead = self.create_lead(line_ids=[(0, 0, {'name': "Line"})])
        self.assertEqual(lead.state, 'draft', "Lead state should be 'draft'")
        self.assertEqual(lead.user_id, self.user_demo, "Responsible should change on creation of Lead test line.")
        self.assertEqual(len(lead.line_ids), 1, "New test line is not created")
        self.assertEqual(lead.line_ids.user_id, self.user_demo, "Responsible should be change on creation of Lead test line.")
