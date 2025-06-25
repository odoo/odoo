# Part of Odoo. See LICENSE file for full copyright and licensing details.

from types import SimpleNamespace
from unittest.mock import patch

from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.http import _request_stack
from odoo.tests import Form, TransactionCase, new_test_user, tagged, HttpCase, users, warmup
from odoo.tools import mute_logger


class UsersCommonCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        users = cls.env['res.users'].create([
            {
                'name': 'Internal',
                'login': 'user_internal',
                'password': 'password',
                'group_ids': [cls.env.ref('base.group_user').id],
                'tz': 'UTC',
            },
            {
                'name': 'Portal 1',
                'login': 'portal_1',
                'password': 'portal_1',
                'group_ids': [cls.env.ref('base.group_portal').id],
            },
            {
                'name': 'Portal 2',
                'login': 'portal_2',
                'password': 'portal_2',
                'group_ids': [cls.env.ref('base.group_portal').id],
            },
        ])

        cls.user_internal, cls.user_portal_1, cls.user_portal_2 = users

        # Remove from the cache the values filled with admin rights for the users/partners that have just been created
        # So unit tests reading/writing these partners/users
        # as other low-privileged users do not have their cache polluted with values fetched with admin rights
        users.partner_id.invalidate_recordset()
        users.invalidate_recordset()


class TestUsers(UsersCommonCase):

    def test_name_search(self):
        """ Check name_search on user. """
        User = self.env['res.users']

        test_user = User.create({'name': 'Flad the Impaler', 'login': 'vlad'})
        like_user = User.create({'name': 'Wlad the Impaler', 'login': 'vladi'})
        other_user = User.create({'name': 'Nothing similar', 'login': 'nothing similar'})
        all_users = test_user | like_user | other_user

        res = User.name_search('vlad', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user)

        res = User.name_search('vlad', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search('', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search('', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, User)

        res = User.name_search('lad', operator='ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user | like_user)

        res = User.name_search('lad', operator='not ilike')
        self.assertEqual(User.browse(i[0] for i in res) & all_users, other_user)

    def test_user_partner(self):
        """ Check that the user partner is well created """

        User = self.env['res.users']
        Partner = self.env['res.partner']
        Company = self.env['res.company']

        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        partner = Partner.create({
            'name': 'Bob Partner',
            'company_id': company_2.id
        })

        # case 1 : the user has no partner
        test_user = User.create({
            'name': 'John Smith',
            'login': 'jsmith',
            'company_ids': [company_1.id],
            'company_id': company_1.id
        })

        self.assertFalse(
            test_user.partner_id.company_id,
            "The partner_id linked to a user should be created without any company_id")

        # case 2 : the user has a partner
        test_user = User.create({
            'name': 'Bob Smith',
            'login': 'bsmith',
            'company_ids': [company_1.id],
            'company_id': company_1.id,
            'partner_id': partner.id
        })

        self.assertEqual(
            test_user.partner_id.company_id,
            company_1,
            "If the partner_id of a user has already a company, it is replaced by the user company"
        )


    def test_change_user_company(self):
        """ Check the partner company update when the user company is changed """

        User = self.env['res.users']
        Company = self.env['res.company']

        test_user = User.create({'name': 'John Smith', 'login': 'jsmith'})
        company_1 = Company.create({'name': 'company_1'})
        company_2 = Company.create({'name': 'company_2'})

        test_user.company_ids += company_1
        test_user.company_ids += company_2

        # 1: the partner has no company_id, no modification
        test_user.write({
            'company_id': company_1.id
        })

        self.assertFalse(
            test_user.partner_id.company_id,
            "On user company change, if its partner_id has no company_id,"
            "the company_id of the partner_id shall NOT be updated")

        # 2: the partner has a company_id different from the new one, update it
        test_user.partner_id.write({
            'company_id': company_1.id
        })

        test_user.write({
            'company_id': company_2.id
        })

        self.assertEqual(
            test_user.partner_id.company_id,
            company_2,
            "On user company change, if its partner_id has already a company_id,"
            "the company_id of the partner_id shall be updated"
        )

    @mute_logger('odoo.sql_db')
    def test_deactivate_portal_users_access(self):
        """Test that only a portal users can deactivate his account."""
        with self.assertRaises(UserError, msg='Internal users should not be able to deactivate their account'):
            self.user_internal._deactivate_portal_user()

    @mute_logger('odoo.sql_db', 'odoo.addons.base.models.res_users_deletion')
    def test_deactivate_portal_users_archive_and_remove(self):
        """Test that if the account can not be removed, it's archived instead
        and sensitive information are removed.

        In this test, the deletion of "portal_user" will succeed,
        but the deletion of "portal_user_2" will fail.
        """
        User = self.env['res.users']
        portal_user = User.create({
            'name': 'Portal',
            'login': 'portal_user',
            'password': 'password',
            'group_ids': [self.env.ref('base.group_portal').id],
        })
        portal_partner = portal_user.partner_id

        portal_user_2 = User.create({
            'name': 'Portal',
            'login': 'portal_user_2',
            'password': 'password',
            'group_ids': [self.env.ref('base.group_portal').id],
        })
        portal_partner_2 = portal_user_2.partner_id

        (portal_user | portal_user_2)._deactivate_portal_user()

        self.assertTrue(portal_user.exists() and not portal_user.active, 'Should have archived the user 1')

        self.assertEqual(portal_user.name, 'Portal', 'Should have kept the user name')
        self.assertEqual(portal_user.partner_id.name, 'Portal', 'Should have kept the partner name')
        self.assertNotEqual(portal_user.login, 'portal_user', 'Should have removed the user login')

        asked_deletion_1 = self.env['res.users.deletion'].search([('user_id', '=', portal_user.id)])
        asked_deletion_2 = self.env['res.users.deletion'].search([('user_id', '=', portal_user_2.id)])

        self.assertTrue(asked_deletion_1, 'Should have added the user 1 in the deletion queue')
        self.assertTrue(asked_deletion_2, 'Should have added the user 2 in the deletion queue')

        # The deletion will fail for "portal_user_2",
        # because of the absence of "ondelete=cascade"
        self.cron = self.env['ir.cron'].create({
            'name': 'Test Cron',
            'user_id': portal_user_2.id,
            'model_id': self.env.ref('base.model_res_partner').id,
        })

        with self.enter_registry_test_mode():
            self.env.ref('base.ir_cron_res_users_deletion').method_direct_trigger()

        self.assertFalse(portal_user.exists(), 'Should have removed the user')
        self.assertFalse(portal_partner.exists(), 'Should have removed the partner')
        self.assertEqual(asked_deletion_1.state, 'done', 'Should have marked the deletion as done')

        self.assertTrue(portal_user_2.exists(), 'Should have kept the user')
        self.assertTrue(portal_partner_2.exists(), 'Should have kept the partner')
        self.assertEqual(asked_deletion_2.state, 'fail', 'Should have marked the deletion as failed')

    def test_user_home_action_restriction(self):
        test_user = new_test_user(self.env, 'hello world')

        # Find an action that contains restricted context ('active_id')
        restricted_action = self.env['ir.actions.act_window'].search([('context', 'ilike', 'active_id')], limit=1)
        with self.assertRaises(ValidationError):
            test_user.action_id = restricted_action.id

        # Find an action without restricted context
        allowed_action = self.env['ir.actions.act_window'].search(['!', ('context', 'ilike', 'active_id')], limit=1)

        test_user.action_id = allowed_action.id
        self.assertEqual(test_user.action_id.id, allowed_action.id)

    def test_context_get_lang(self):
        self.env['res.lang'].with_context(active_test=False).search([
            ('code', 'in', ['fr_FR', 'es_ES', 'de_DE', 'en_US'])
        ]).write({'active': True})

        user = new_test_user(self.env, 'jackoneill')
        user = user.with_user(user)
        user.lang = 'fr_FR'

        company = user.company_id.partner_id.sudo()
        company.lang = 'de_DE'

        request = SimpleNamespace()
        request.best_lang = 'es_ES'
        request_patch = patch('odoo.addons.base.models.res_users.request', request)
        self.addCleanup(request_patch.stop)
        request_patch.start()

        self.assertEqual(user.context_get()['lang'], 'fr_FR')
        self.env.registry.clear_cache()
        user.lang = False

        self.assertEqual(user.context_get()['lang'], 'es_ES')
        self.env.registry.clear_cache()
        request_patch.stop()

        self.assertEqual(user.context_get()['lang'], 'de_DE')
        self.env.registry.clear_cache()
        company.lang = False

        self.assertEqual(user.context_get()['lang'], 'en_US')

    def test_user_self_update(self):
        """ Check that the user has access to write his phone. """
        test_user = self.env['res.users'].create({'name': 'John Smith', 'login': 'jsmith'})
        self.assertFalse(test_user.phone)
        test_user.with_user(test_user).write({'phone': '2387478'})

        self.assertEqual(
            test_user.partner_id.phone,
            '2387478',
            "The phone of the partner_id shall be updated."
        )

    def test_session_non_existing_user(self):
        """
        Test to check the invalidation of session bound to non existing (or deleted) users.
        """
        User = self.env['res.users']
        last_user_id = User.with_context(active_test=False).search([], limit=1, order="id desc")
        non_existing_user = User.browse(last_user_id.id + 1)
        self.assertFalse(non_existing_user._compute_session_token('session_id'))

@tagged('post_install', '-at_install', 'groups')
class TestUsers2(UsersCommonCase):

    def test_change_user_login(self):
        """ Check that partner email is updated when changing user's login """

        User = self.env['res.users']
        with Form(User, view='base.view_users_simple_form') as UserForm:
            UserForm.name = "Test User"
            UserForm.login = "test-user1"
            self.assertFalse(UserForm.email)

            UserForm.login = "test-user1@mycompany.example.org"
            self.assertEqual(
                UserForm.email, "test-user1@mycompany.example.org",
                "Setting a valid email as login should update the partner's email"
            )

    def test_default_groups(self):
        """ The groups handler doesn't use the "real" view with pseudo-fields
        during installation, so it always works (because it uses the normal
        group_ids field).
        """
        default_group = self.env.ref('base.default_user_group')
        test_group = self.env['res.groups'].create({'name': 'test_group'})
        default_group.implied_ids = test_group

        # use the specific views which has the pseudo-fields
        f = Form(self.env['res.users'], view='base.view_users_form')
        f.name = "bob"
        f.login = "bob"
        user = f.save()

        group_user = self.env.ref('base.group_user')

        self.assertIn(group_user, user.group_ids)
        self.assertEqual(default_group.implied_ids + group_user, user.group_ids)

    def test_selection_groups(self):
        # create 3 groups that should be in a selection
        app = self.env['res.groups.privilege'].create({'name': 'Foo'})
        group_user, group_manager, group_visitor = self.env['res.groups'].create([
            {'name': name, 'privilege_id': app.id}
            for name in ('User', 'Manager', 'Visitor')
        ])
        # THIS PART IS NECESSARY TO REPRODUCE AN ISSUE: group1.id < group2.id < group0.id
        self.assertLess(group_user.id, group_manager.id)
        self.assertLess(group_manager.id, group_visitor.id)
        # implication order is group0 < group1 < group2
        group_manager.implied_ids = group_user
        group_user.implied_ids = group_visitor
        groups = group_visitor + group_user + group_manager

        # create a user
        user = self.env['res.users'].create({'name': 'foo', 'login': 'foo'})

        # put user in group_visitor, and check field value
        user.write({'group_ids': [Command.set([group_visitor.id])]})
        self.assertEqual(user.group_ids & groups, group_visitor)
        self.assertEqual(user.all_group_ids & groups, group_visitor)
        self.assertEqual(user.read(['group_ids'])[0]['group_ids'], [group_visitor.id])
        self.assertEqual(user.read(['all_group_ids'])[0]['all_group_ids'], [group_visitor.id])

        # remove group_visitor
        user.write({'group_ids': [Command.unlink(group_visitor.id)]})
        self.assertEqual(user.group_ids & groups, self.env['res.groups'])

        # put user in group_manager, and check field value
        user.write({'group_ids': [Command.set([group_manager.id])]})
        self.assertEqual(user.group_ids & groups, group_manager)
        self.assertEqual(user.all_group_ids & groups, group_visitor + group_manager + group_user)
        self.assertEqual(user.read(['group_ids'])[0]['group_ids'], [group_manager.id])
        self.assertEqual(set(user.read(['all_group_ids'])[0]['all_group_ids']), set((group_visitor + group_manager + group_user).ids))

        # add user in group_user, and check field value
        user.write({'group_ids': [Command.link(group_user.id)]})
        self.assertEqual(user.group_ids & groups, group_manager + group_user)
        self.assertEqual(user.all_group_ids & groups, group_visitor + group_manager + group_user)
        self.assertEqual(set(user.read(['group_ids'])[0]['group_ids']), set((group_manager + group_user).ids))
        self.assertEqual(set(user.read(['all_group_ids'])[0]['all_group_ids']), set((group_visitor + group_manager + group_user).ids))

        groups = self.env['res.groups'].search([('all_user_ids', '=', user.id)])
        self.assertEqual(groups, user.all_group_ids)

    def test_implied_groups_on_change(self):
        """Test that a change on a reified fields trigger the onchange of group_ids."""
        group_public = self.env.ref('base.group_public')
        group_portal = self.env.ref('base.group_portal')
        group_user = self.env.ref('base.group_user')

        app = self.env['res.groups.privilege'].create({'name': 'Foo'})
        group_contain_user = self.env['res.groups'].create({
            'name': 'Small user group',
            'privilege_id': app.id,
            'implied_ids': [group_user.id],
        })

        user_form = Form(self.env['res.users'], view='base.view_users_form')
        user_form.name = "Test"
        user_form.login = "Test"
        self.assertFalse(user_form.share)

        user_form['group_ids'] = group_portal
        self.assertTrue(user_form.share, 'The group_ids onchange should have been triggered')

        user = user_form.save()

        # in debug mode, show the group widget for external user

        with self.debug_mode():
            user_form = Form(user, view='base.view_users_form')

            user_form['group_ids'] = group_user
            self.assertFalse(user_form.share, 'The group_ids onchange should have been triggered')

            user_form['group_ids'] = group_public
            self.assertTrue(user_form.share, 'The group_ids onchange should have been triggered')

            user_form['group_ids'] = group_user
            user_form['group_ids'] = group_user + group_contain_user

            user_form.save()

        # in debug mode, allow extra groups

        with self.debug_mode():
            user_form = Form(self.env['res.users'], view='base.view_users_form')
            user_form.name = "Test-2"
            user_form.login = "Test-2"

            user_form['group_ids'] = group_portal
            self.assertTrue(user_form.share)

            # for portal user, the view_group_extra_ids is only show in debug mode
            user_form['group_ids'] = group_portal + group_contain_user
            self.assertFalse(user_form.share, 'The group_ids onchange should have been triggered')

            with self.assertRaises(ValidationError, msg="The user cannot be at the same time in groups: ['Membre', 'Portal', 'Foo / Small user group']"):
                user_form.save()

    @users('portal_1')
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_self_writeable_fields(self):
        """Check that a portal user:
            - can write on fields in SELF_WRITEABLE_FIELDS on himself,
            - cannot write on fields not in SELF_WRITEABLE_FIELDS on himself,
            - and none of the above on another user than himself.
        """
        self.assertIn(
            "post_install",
            self.test_tags,
            "This test **must** be `post_install` to ensure the expected behavior despite other modules",
        )
        self.assertIn(
            "email",
            self.env['res.users'].SELF_WRITEABLE_FIELDS,
            "For this test to make sense, 'email' must be in the `SELF_WRITEABLE_FIELDS`",
        )
        self.assertNotIn(
            "login",
            self.env['res.users'].SELF_WRITEABLE_FIELDS,
            "For this test to make sense, 'login' must not be in the `SELF_WRITEABLE_FIELDS`",
        )

        me = self.env["res.users"].browse(self.env.user.id)
        other = self.env["res.users"].browse(self.user_portal_2.id)

        # Allow to write a field in the SELF_WRITEABLE_FIELDS
        me.email = "foo@bar.com"
        self.assertEqual(me.email, "foo@bar.com")
        # Disallow to write a field not in the SELF_WRITEABLE_FIELDS
        with self.assertRaises(AccessError):
            me.login = "foo"

        # Disallow to write a field in the SELF_WRITEABLE_FIELDS on another user
        with self.assertRaises(AccessError):
            other.email = "foo@bar.com"
        # Disallow to write a field not in the SELF_WRITEABLE_FIELDS on another user
        with self.assertRaises(AccessError):
            other.login = "foo"

    @users('user_internal')
    def test_self_readable_writeable_fields_preferences_form(self):
        """Test that a field protected by a `groups='...'` with a group the user doesn't belong to
        but part of the `SELF_WRITEABLE_FIELDS` is shown in the user profile preferences form and is editable"""
        my_user = self.env['res.users'].browse(self.env.user.id)
        self.assertIn(
            'name',
            my_user.SELF_WRITEABLE_FIELDS,
            "This test doesn't make sense if not tested on a field part of the SELF_WRITEABLE_FIELDS"
        )
        self.patch(self.env.registry['res.users']._fields['name'], 'groups', 'base.group_system')
        with Form(my_user, view='base.view_users_form_simple_modif') as UserForm:
            UserForm.name = "Raoulette Poiluchette"
        self.assertEqual(my_user.name, "Raoulette Poiluchette")

    @warmup
    def test_write_group_ids_performance(self):
        contact_creation_group = self.env.ref("base.group_partner_manager")
        self.assertNotIn(contact_creation_group, self.user_internal.group_ids)

        # all modules: 23, base: 10; nightly: +1
        with self.assertQueryCount(24):
            self.user_internal.write({
                "group_ids": [Command.link(contact_creation_group.id)],
            })


class TestUsersTweaks(TransactionCase):
    def test_superuser(self):
        """ The superuser is inactive and must remain as such. """
        user = self.env['res.users'].browse(SUPERUSER_ID)
        self.assertFalse(user.active)
        with self.assertRaises(UserError):
            user.write({'active': True})


@tagged('post_install', '-at_install')
class TestUsersIdentitycheck(HttpCase):

    @users('admin')
    def test_revoke_all_devices(self):
        """
        Test to check the revoke all devices by changing the current password as a new password
        """
        # Change the password to 8 characters for security reasons
        self.env.user.password = "admin@odoo"

        # Create a first session that will be used to revoke other sessions
        session = self.authenticate('admin', 'admin@odoo')

        # Create a second session that will be used to check it has been revoked
        self.authenticate('admin', 'admin@odoo')
        # Test the session is valid
        # Valid session -> not redirected from /web to /web/login
        self.assertTrue(self.url_open('/web').url.endswith('/web'))

        # Push a fake request to the request stack, because @check_identity requires a request.
        # Use the first session created above, used to invalid other sessions than itself.
        _request_stack.push(SimpleNamespace(session=session, env=self.env))
        self.addCleanup(_request_stack.pop)
        # The user clicks the button logout from all devices from his profile
        action = self.env.user.action_revoke_all_devices()
        # The form of the check identity wizard opens
        form = Form(self.env[action['res_model']].browse(action['res_id']), action.get('view_id'))
        # The user fills his password
        form.password = 'admin@odoo'
        # The user clicks the button "Log out from all devices", which triggers a save then a call to the button method
        user_identity_check = form.save()
        action = user_identity_check.with_context(password=form.password).run_check()

        # Test the session is no longer valid
        # Invalid session -> redirected from /web to /web/login
        self.assertTrue(self.url_open('/web').url.endswith('/web/login?redirect=%2Fweb%3F'))

        # In addition, the password must have been emptied from the wizard
        self.assertFalse(user_identity_check.password)
