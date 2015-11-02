from openerp import SUPERUSER_ID
from openerp.tests import common
from .. import test_models

@common.at_install(False)
@common.post_install(True)
class base_action_rule_test(common.TransactionCase):

    def setUp(self):
        super(base_action_rule_test, self).setUp()
        self.user_admin = self.env.ref('base.user_root')
        self.user_demo = self.env.ref('base.user_demo')

    def create_lead(self, **kwargs):
        vals = {
            'name': "Lead Test",
            'user_id': self.user_admin.id,
        }
        vals.update(kwargs)
        return self.env['base.action.rule.lead.test'].create(vals)

    def test_00_check_to_state_open_pre(self):
        """
        Check that a new record (with state = open) doesn't change its responsible
        when there is a precondition filter which check that the state is open.
        """
        lead = self.create_lead(state='open')
        self.assertEqual(lead.state, 'open')
        self.assertEqual(lead.user_id, self.user_admin)

    def test_01_check_to_state_draft_post(self):
        """
        Check that a new record changes its responsible when there is a postcondition
        filter which check that the state is draft.
        """
        lead = self.create_lead()
        self.assertEqual(lead.state, 'draft')
        self.assertEqual(lead.user_id, self.user_demo)

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
        self.assertEqual(lead.state, 'open')
        self.assertEqual(lead.user_id, self.user_admin)
        # change state to pending and check that responsible has not changed
        lead.write({'state': 'pending'})
        self.assertEqual(lead.state, 'pending')
        self.assertEqual(lead.user_id, self.user_admin)
        # change state to done and check that responsible has not changed
        lead.write({'state': 'done'})
        self.assertEqual(lead.state, 'done')
        self.assertEqual(lead.user_id, self.user_admin)

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
        self.assertEqual(lead.state, 'open')
        self.assertEqual(lead.user_id, self.user_admin)
        # change state to done and check that responsible has changed
        lead.write({'state': 'done'})
        self.assertEqual(lead.state, 'done')
        self.assertEqual(lead.user_id, self.user_demo)

    def test_04_recomputed_field(self):
        """
        Check that a rule is executed whenever a field is recomputed after a
        change on another model.
        """
        partner = self.env.ref('base.res_partner_1')
        partner.write({'customer': False})
        lead = self.create_lead(state='open', partner_id=partner.id)
        self.assertFalse(lead.customer)
        self.assertEqual(lead.user_id, self.user_admin)
        # change partner, recompute on lead should trigger the rule
        partner.write({'customer': True})
        self.assertTrue(lead.customer)
        self.assertEqual(lead.user_id, self.user_demo)
