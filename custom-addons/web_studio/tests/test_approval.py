from psycopg2 import IntegrityError

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestStudioApproval(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        creation_context =  {
            "studio": True,
            'no_reset_password': True,
            'mail_create_nosubscribe': True,
            'mail_create_nolog': True
        }
        # setup 2 users with custom groups
        cls.group_user = cls.env['res.groups'].with_context(**creation_context).create({
            'name': 'Approval User',
            'implied_ids': [(4, cls.env.ref('base.group_user').id)],
        })
        cls.group_manager = cls.env['res.groups'].with_context(**creation_context).create({
            'name': 'Approval Manager',
            'implied_ids': [(4, cls.group_user.id)],
        })
        cls.user = mail_new_test_user(
            cls.env, login='Employee',
            groups="base.group_user,base.group_partner_manager", context=creation_context)
        cls.manager = mail_new_test_user(
            cls.env, login='Manager',
            groups="base.group_user,base.group_partner_manager", context=creation_context)
        cls.user.write({
            'groups_id': [(4, cls.group_user.id)]
        })
        cls.manager.write({
            'groups_id': [(4, cls.group_manager.id)]
        })
        cls.record = cls.user.partner_id
        # setup validation rules; inactive by default, they'll get
        # activated in the tests when they're needed
        # i'll use the 'open_parent' method on partners because why not
        partner_model = cls.env.ref('base.model_res_partner')
        cls.MODEL = 'res.partner'
        cls.METHOD = 'open_parent'
        cls.rule = cls.env['studio.approval.rule'].create({
            'active': False,
            'model_id': partner_model.id,
            'method': cls.METHOD,
            'message': "You didn't say the magic word!",
            'group_id': cls.group_manager.id,
        })
        cls.rule_with_domain = cls.env['studio.approval.rule'].create({
            'active': False,
            'model_id': partner_model.id,
            'method': cls.METHOD,
            'message': "You didn't say the magic word!",
            'group_id': cls.group_manager.id,
            'domain': '[("is_company", "=", True)]',
        })
        cls.rule_exclusive = cls.env['studio.approval.rule'].create({
            'active': False,
            'model_id': partner_model.id,
            'method': cls.METHOD,
            'message': "You didn't say the magic word!",
            'group_id': cls.group_manager.id,
            'exclusive_user': True,
        })
        cls.rule_exclusive_with_domain = cls.env['studio.approval.rule'].create({
            'active': False,
            'model_id': partner_model.id,
            'method': cls.METHOD,
            'message': "You didn't say the magic word!",
            'group_id': cls.group_manager.id,
            'domain': '[("is_company", "=", True)]',
            'exclusive_user': True,
        })

    def test_00_constraints(self):
        """Check that constraints on the model apply as expected."""
        self.rule.active = True
        # check that approval rules on non-existing methods are not allowed
        with self.assertRaises(ValidationError, msg="Shouldn't have approval on non-existing method"):
            self.rule.method = 'atomize'
        # check that there cannot be 2 entries for the same rule+record
        self.rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=False)
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError, msg="Shouldn't have 2 entries for the same rule+record"):
                with self.cr.savepoint():
                    self.env['studio.approval.entry'].with_user(self.manager).create({
                        'rule_id': self.rule.id,
                        'user_id': self.manager.id,
                        'res_id': self.record.id,
                    })
        # check that modifying forbidden fields is prevented when entries exist
        with self.assertRaises(UserError):
            self.rule.method = 'unlink'
        with self.assertRaises(UserError):
            self.rule.group_id = self.env.ref('base.group_user')
        with self.assertRaises(UserError):
            self.rule.model_id = self.env.ref('base.model_res_partner_bank')
        with self.assertRaises(UserError):
            self.rule.action_id = self.env['ir.actions.actions'].search([], limit=1)
        # check that deleting a rule that has entries is prevented
        with self.assertRaises(UserError):
            self.rule.unlink()

    def test_01_single_rule(self):
        """ - normal user can't validate
            - normal user can't proceed
            - admin user can validate
            - normal user can proceed after that
        """
        rule = self.rule
        rule.active = True
        with self.assertRaises(UserError, msg="Should'nt validate without required group"):
            rule.with_user(self.user).set_approval(res_id=self.record.id, approved=True)
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'), "Shouldn't have approved automatically")
        rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=True)
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertTrue(approval_result.get('approved'), "Should be able to proceed after manager approval")

    def test_02_single_rule_on_action(self):
        """ Same as previous test, but with approval on an action instead of a method."""
        rule = self.rule
        # there's no constraint on actions, since any action could be set
        # in the form view's arch; take a random action
        ACTION = self.env.ref('base.action_partner_form')
        rule.write({
            'active': True,
            'method': False,
            'action_id': ACTION.id,
        })
        with self.assertRaises(UserError, msg="Should'nt validate without required group"):
            rule.with_user(self.user).set_approval(res_id=self.record.id, approved=True)
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=False,
            action_id=ACTION.id)
        self.assertFalse(approval_result.get('approved'), "Shouldn't have approved automatically")
        rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=True)
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=False,
            action_id=ACTION.id)
        self.assertTrue(approval_result.get('approved'), "Should be able to proceed after manager approval")

    def test_03_single_rule_with_domain(self):
        """ - rule not triggered if no domain match
            - rule triggered if domain match
        """
        rule = self.rule_with_domain
        rule.active = True
        matching_record = self.env.ref('base.main_company').partner_id
        non_matching_record = self.record
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=matching_record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'), "Shouldn't be able to proceed on record that matches the rule's domain")
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=non_matching_record.id,
            method=self.METHOD,
            action_id=False)
        self.assertTrue(approval_result.get('approved'), "Should be able to proceed on record that doesn't match the rule's domain")

    def test_04_rule_rejection(self):
        """ - admin rejects rule
            - normal user can't proceed
            - admin user can't proceed
            - admin approves rule
            - normal user can proceed
        """
        rule = self.rule
        rule.active = True
        rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=False)
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'), "User shouldn't be able to proceed following manager rejection")
        approval_result = self.env['studio.approval.rule'].with_user(self.manager).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'), "Manager shouldn't be able to proceed following own rejection")
        rule.with_user(self.manager).delete_approval(res_id=self.record.id)
        rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=True)
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertTrue(approval_result.get('approved'), "Should be able to proceed after manager changed their mind")

    def test_05_different_users(self):
        """ - user cannot proceed
            - admin cannot proceed
            - admin can validate their rule and proceed
            - user can approve their rule and proceed after manager approval
        """
        # set the base rule for users and the 'exlusive_user' rules for admin
        self.rule.active = True
        self.rule.group_id = self.group_user
        self.rule_exclusive.active = True
        user_rule = self.rule
        manager_rule = self.rule_exclusive
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'), "User shouldn't be able to proceed")
        # cancel the user's approval which was implicitely done in the previous call
        user_rule.with_user(self.user).delete_approval(res_id=self.record.id)
        approval_result = self.env['studio.approval.rule'].with_user(self.manager).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'), "Manager shouldn't be able to proceed")
        approval_info = self.env['studio.approval.rule'].with_user(self.manager).get_approval_spec(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False
        )
        manager_entry = list(filter(lambda e: e['user_id'][0] == self.manager.id, approval_info['entries']))
        self.assertEqual(len(manager_entry), 1, "Only one rule should have been validated by the manager")
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertTrue(approval_result.get('approved'), "Should be able to proceed after everybody approved")

    def test_06_security(self):
        """ - user cannot remove entry from admin
            - admin cannot remove entry from user
            - rule already validated/rejected doesn't accept new validation
        """
        # set the base rule for users and the 'exlusive_user' rules for admin
        self.rule.active = True
        self.rule.group_id = self.group_user
        self.rule_exclusive.active = True
        user_rule = self.rule
        manager_rule = self.rule_exclusive
        user_rule.with_user(self.user).set_approval(res_id=self.record.id, approved=False)
        manager_rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=False)
        with self.assertRaises(UserError, msg="Shouldn't be able to cancel approval of someone else"):
            user_rule.with_user(self.manager).delete_approval(res_id=self.record.id)
        with self.assertRaises(UserError, msg="Shouldn't be able to create a second entry for the same record+rule"):
            user_rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=True)
            self.env.flush_all()
        with self.assertRaises(UserError, msg="Shouldn't be able to cancel approval of someone else"):
            manager_rule.with_user(self.user).delete_approval(res_id=self.record.id)
        with self.assertRaises(UserError, msg="Shouldn't be able to create a second entry for the same record+rule"):
            manager_rule.with_user(self.user).set_approval(res_id=self.record.id, approved=True)
            self.env.flush_all()

    def test_07_forbidden_record(self):
        """Getting/setting approval on records to which you don't have access."""
        MODEL = 'res.company'
        METHOD = 'write_company_and_print_report'
        main_company = self.manager.company_id
        alternate_company = self.env['res.company'].create({'name': 'SomeCompany'})
        self.rule.write({
            'active': True,
            'method': METHOD,
            'model_id': self.env.ref('base.model_res_company').id,
        })
        # I don't need to assert anything: raise = failure
        self.env['studio.approval.rule'].with_user(self.manager).get_approval_spec(
            model=MODEL,
            res_id=main_company.id,
            method=METHOD,
            action_id=False
        )
        with self.assertRaises(AccessError, msg="Shouldn't be able to get approval spec on record I can't read"):
            self.env['studio.approval.rule'].with_user(self.manager).get_approval_spec(
                model=MODEL,
                res_id=alternate_company.id,
                method=METHOD,
                action_id=False
            )
        with self.assertRaises(AccessError, msg="Shouldn't be able to set approval on record I can't write on"):
            self.rule.with_user(self.manager).set_approval(res_id=main_company.id, approved=True)

    def test_08_archive(self):
        """Archiving of approvals should be applied even with active_test disabled."""
        # set the base rule for users and the 'exclusive_user' rules for admin
        self.rule.active = True
        self.rule.group_id = self.group_user
        self.rule_exclusive.active = True
        manager_rule = self.rule_exclusive
        approval_result = self.env['studio.approval.rule'].with_user(self.manager).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'), "Manager shouldn't be able to proceed")
        manager_rule.active = False
        approval_result = self.env['studio.approval.rule'].with_context(active_test=False).with_user(self.manager).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertTrue(approval_result.get('approved'), "Manager should be able to proceed with archived rule even with active_test disabled")

    def test_09_archive_reverse(self):
        """Archiving of rules should not prevent rules with 'exclusive_user' from working."""
        # set the base rule for users and the 'exclusive_user' rules for admin
        self.rule.active = True
        self.rule.group_id = self.group_user
        self.rule_exclusive.active = True
        non_exlusive_rule = self.rule
        # validate a rule that is not exclusive then archive it
        non_exlusive_rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=True)
        non_exlusive_rule.active = False
        # try to approve an exclusive rule which is still remaining
        approval_result = self.env['studio.approval.rule'].with_user(self.manager).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertTrue(approval_result.get('approved'), "should be able to proceed with an exclusive rule if another entry was archived")

    def test_10_exclusive_collision(self):
        """Test that exclusive rules for different methods does not interact unexpectdedly."""
        # set the base rule for users and the 'exlusive_user' rules for admin
        self.rule.active = True
        self.rule.group_id = self.group_user
        self.rule_exclusive.active = True
        self.rule_exclusive.group_id = self.group_user
        other_exclusive_rule = self.env['studio.approval.rule'].create({
            'active': True,
            'model_id': self.rule_exclusive.model_id.id,
            'method': 'main_partner',
            'message': "You didn't say the magic word!",
            'group_id': self.group_user.id,
            'exclusive_user': True,
        })
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'), "User shouldn't be able to proceed")
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method='main_partner',
            action_id=False)
        # check that the rule on 'unlink' is not prevented by another entry
        # for a rule that is not related to the same action/method
        self.assertTrue(approval_result.get('approved'), "User should be able to unlink")

    def test_11_approval_activity(self):
        """Test the integration between approvals and next activities"""
        self.rule.active = True
        self.rule.responsible_id = self.manager
        # generate a next activity for the rule's responsible by asking for approval
        self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        approval_request = self.env['studio.approval.request'].search(
            [('rule_id', '=', self.rule.id), ('res_id', '=', self.record.id)])
        self.assertEqual(len(approval_request), 1, "There should be exactly one approval request")
        activity = approval_request.mail_activity_id
        # mark the activity as done, the approval should go through and the request should be deleted
        activity.with_user(self.manager).action_done()
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertTrue(approval_result.get('approved'),
                        "The approval should have been granted upon validation of the activity")
        self.assertFalse(approval_request.exists(),
                         "The approval request should have been deleted upon the activity's confirmation")

    def test_12_approval_activity_spoof(self):
        """Test that validating an approval activity as another user will not leak approval rights"""
        self.rule.active = True
        self.rule.responsible_id = self.manager
        # generate a next activity for the rule's responsible by asking for approval
        self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        approval_request = self.env['studio.approval.request'].search(
            [('rule_id', '=', self.rule.id), ('res_id', '=', self.record.id)])
        activity = approval_request.mail_activity_id
        # mark the manager's activity as done with the non-manager user
        # the approval should *not* go through and the request should be deleted (and no errors should be raised)
        activity.with_user(self.user).action_done()
        approval_result = self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        self.assertFalse(approval_result.get('approved'),
                         "The approval should not have been granted upon validation of the activity by anohter user")
        self.assertFalse(approval_request.exists(),
                         "The approval request should have been deleted upon the activity's confirmation")

    def test_13_approval_activity_dismissal(self):
        """Test that granting approval unlinks the activity that was created for that purpose"""
        self.rule.active = True
        self.rule.responsible_id = self.manager
        # generate a next activity for the rule's responsible by asking for approval
        self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        approval_request = self.env['studio.approval.request'].search(
            [('rule_id', '=', self.rule.id), ('res_id', '=', self.record.id)])
        activity = approval_request.mail_activity_id
        # grant approval as the manager
        # both the mail activity and the approval requested should be deleted
        self.rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=True)
        self.assertFalse(activity.exists(),
                         "The activity should have been deleted if approval was granted through another channel")
        self.assertFalse(approval_request.exists(),
                         "The approval request should have been deleted when the approval was granted")

    def test_14_approval_activity_dismissal_refused(self):
        """Test that granting approval unlinks the activity that was created for that purpose"""
        self.rule.active = True
        self.rule.responsible_id = self.manager
        # generate a next activity for the rule's responsible by asking for approval
        self.env['studio.approval.rule'].with_user(self.user).check_approval(
            model=self.MODEL,
            res_id=self.record.id,
            method=self.METHOD,
            action_id=False)
        approval_request = self.env['studio.approval.request'].search(
            [('rule_id', '=', self.rule.id), ('res_id', '=', self.record.id)])
        activity = approval_request.mail_activity_id
        # refuse the approval as the manager
        # both the mail activity and the approval requested should be deleted
        self.rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=False)
        self.assertFalse(activity.exists(),
                         "The activity should have been deleted if approval was refused through another channel")
        self.assertFalse(approval_request.exists(),
                         "The approval request should have been deleted when the approval was refused")

    def test_15_approval_notification_order(self):
        """Test the multi-levels of approvals"""
        self.rule.active = True
        self.rule.responsible_id = self.manager
        self.rule.notification_order = '2'
        self.rule.message = 'This approval is the second step of approval'
        lower_level_rule = self.env['studio.approval.rule'].create({
            'active': True,
            'model_id': self.rule.model_id.id,
            'method': self.rule.method,
            'message': 'This approval is the first step of approval',
            'group_id': self.group_user.id,
        })
        lower_level_rule.responsible_id = self.manager
        # only the rule of level 1 should create a request for approval activity
        request_level_1 = lower_level_rule._create_request(self.record.id)
        request_level_2 = self.rule._create_request(self.record.id)
        self.assertTrue(request_level_1, "An approval request has been created for the level 1 rule")
        self.assertFalse(request_level_2, "No approval request has been created for the level 2 rule")
        # now approve the first request, which will automatically create a request for level 2 rule
        lower_level_rule.with_user(self.manager).set_approval(res_id=self.record.id, approved=True)
        request_level_1 = lower_level_rule._create_request(self.record.id)
        request_level_2 = self.rule._create_request(self.record.id)
        self.assertFalse(request_level_2, "No approval request can be created for the level 2 rule")

@tagged('post_install', '-at_install')
class TestStudioApprovalPost(TransactionCase):
    # patching is done when the registry is ready, so post-install is needed

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        creation_context = {
            "studio": True,
            'no_reset_password': True,
            'mail_create_nosubscribe': True,
            'mail_create_nolog': True
        }
        # setup 2 users with custom groups
        cls.group_user = cls.env['res.groups'].with_context(**creation_context).create({
            'name': 'Approval User',
            'implied_ids': [(4, cls.env.ref('base.group_user').id)],
        })
        cls.group_manager = cls.env['res.groups'].with_context(**creation_context).create({
            'name': 'Approval Manager',
            'implied_ids': [(4, cls.group_user.id)],
        })
        cls.user = mail_new_test_user(
            cls.env, login='Employee',
            groups="base.group_user,base.group_partner_manager", context=creation_context)
        cls.manager = mail_new_test_user(
            cls.env, login='Manager',
            groups="base.group_user,base.group_partner_manager", context=creation_context)
        cls.user.write({
            'groups_id': [(4, cls.group_user.id)]
        })
        cls.manager.write({
            'groups_id': [(4, cls.group_manager.id)]
        })
        cls.record = cls.user.partner_id
        # setup validation rules; inactive by default, they'll get
        # activated in the tests when they're needed
        # i'll use the 'open_parent' method on partners because why not
        cls.MODEL = 'res.partner'
        cls.METHOD = 'open_parent'

    def test_approval_method_patch(self):
        """Test that creating an approval rule causes a patch of the model method."""
        # Test the approval patching with "open_commercial_entity" method from res.partner
        # but it could have been done on another method or another model."

        partner = self.env['res.partner'].with_user(self.user).search([])[0]

        # the method is not patched
        self.assertFalse(hasattr(partner.with_user(self.user).open_commercial_entity, 'studio_approval_rule_origin'), 'The\
                         method should not be patched')

        origin_result = partner.with_user(self.user).open_commercial_entity()

        rule = self.env['studio.approval.rule'].create({
            'active': True,
            'model_id': self.env.ref('base.model_res_partner').id,
            'method': 'open_commercial_entity',
            'message': "You didn't say the magic word!",
            'group_id': self.group_manager.id,
        })

        # the method is patched
        self.assertTrue(hasattr(partner.with_user(self.user).open_commercial_entity, 'studio_approval_rule_origin'), 'The\
                         method should be patched')

        # the method is well patched and the user don't have the approval authorization. The return
        # should be a notification action
        partner = self.env['res.partner'].with_user(self.user).search([])[0]
        user_result = partner.with_user(self.user).open_commercial_entity()
        self.assertTrue(user_result.get('type') == 'ir.actions.client' and user_result.get('tag') == 'display_notification', 'The patched method should return a notification action')
        self.assertEqual(user_result.get('params', {}).get('title'), 'The following approvals are missing:', 'The notification should have the correct title')
        self.assertEqual(user_result.get('params', {}).get('message'), "You didn't say the magic word!", 'The notification contains the corresponding message')
        self.assertEqual(user_result.get('params', {}).get('type'), 'warning', 'The notification should be a warning')

        # the manager can indeed execute this method
        manager_result = partner.with_user(self.manager).open_commercial_entity()
        self.assertDictEqual(manager_result, origin_result, 'The patch should execute the original method')

        # with the write, the method should not be patched anymore
        rule.write({'active': False})
        self.assertFalse(hasattr(partner.with_user(self.user).open_commercial_entity, 'studio_approval_rule_origin'), 'The\
                         method should not be patched anymore')

        # sanity check, the user has access to the method
        user_result = partner.with_user(self.user).open_commercial_entity()
        self.assertEqual(user_result.get('type'), 'ir.actions.act_window', 'Should execute the original method')

    def test_approval_method_patch_sudo(self):
        """Test that a patched method will bypass approval checks in a sudoed env."""
        # Test the approval patching with "open_commercial_entity" method from res.partner
        # but it could have been done on another method or another model."

        partner = self.env['res.partner'].with_user(self.user).search([])[0]
        origin_result = partner.with_user(self.user).open_commercial_entity()

        self.env['studio.approval.rule'].create({
            'active': True,
            'model_id': self.env.ref('base.model_res_partner').id,
            'method': 'open_commercial_entity',
            'message': "You didn't say the magic word!",
            'group_id': self.group_manager.id,
        })
        # the method is well patched and the user don't have the approval authorization
        # however if we sudo the user, the method should be executed nonetheless
        partner = self.env['res.partner'].with_user(self.user).search([])[0]
        user_result = partner.with_user(self.user).sudo().open_commercial_entity()
        self.assertDictEqual(user_result, origin_result, 'The patch should execute the original method')

    def test_approval_methods_protection(self):
        """Test that some methods we do not want to patch are well protected"""

        with self.assertRaises(ValidationError):
            self.env['studio.approval.rule'].create({
                'active': True,
                'model_id': self.env.ref('base.model_res_partner').id,
                'method': '_get_gravatar_image',
                'message': "You didn't say the magic word!",
                'group_id': self.group_manager.id,
            })

        with self.assertRaises(ValidationError):
            self.env['studio.approval.rule'].create({
                'active': True,
                'model_id': self.env.ref('base.model_res_partner').id,
                'method': '__setattr__',
                'message': "You didn't say the magic word!",
                'group_id': self.group_manager.id,
            })

        with self.assertRaises(ValidationError):
            self.env['studio.approval.rule'].create({
                'active': True,
                'model_id': self.env.ref('base.model_res_partner').id,
                'method': 'create',
                'message': "You didn't say the magic word!",
                'group_id': self.group_manager.id,
            })

        with self.assertRaises(ValidationError):
            self.env['studio.approval.rule'].create({
                'active': True,
                'model_id': self.env.ref('base.model_res_partner').id,
                'method': 'write',
                'message': "You didn't say the magic word!",
                'group_id': self.group_manager.id,
            })

        with self.assertRaises(ValidationError):
            self.env['studio.approval.rule'].create({
                'active': True,
                'model_id': self.env.ref('base.model_res_partner').id,
                'method': 'unlink',
                'message': "You didn't say the magic word!",
                'group_id': self.group_manager.id,
            })
