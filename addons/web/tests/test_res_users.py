# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests.common import tagged


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResUsers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = cls.env["res.users"].create([
            {'name': 'Jean', 'login': 'jean@mail.com', 'password': 'jean@mail.com'},
            {'name': 'Jean-Paul', 'login': 'jean-paul@mail.com', 'password': 'jean-paul@mail.com'},
            {'name': 'Jean-Jacques', 'login': 'jean-jacques@mail.com', 'password': 'jean-jacques@mail.com'},
            {'name': 'Georges', 'login': 'georges@mail.com', 'password': 'georges@mail.com'},
            {'name': 'Claude', 'login': 'claude@mail.com', 'password': 'claude@mail.com'},
            {'name': 'Pascal', 'login': 'pascal@mail.com', 'password': 'pascal@mail.com'},
        ])

    def test_name_search(self):
        """
        Test name search with self assign feature
        The self assign feature is present only when a limit is present,
        which is the case with the public name_search by default
        """
        ResUsers = self.env['res.users']
        jean = self.users[0]
        user_ids = [id_ for id_, __ in ResUsers.with_user(jean).name_search('')]
        self.assertEqual(jean.id, user_ids[0], "The current user, Jean, should be the first in the result.")
        user_ids = [id_ for id_, __ in ResUsers.with_user(jean).name_search('Claude')]
        self.assertNotIn(jean.id, user_ids, "The current user, Jean, should not be in the result because his name does not fit the condition.")
        pascal = self.users[-1]
        user_ids = [id_ for id_, __ in ResUsers.with_user(pascal).name_search('')]
        self.assertEqual(pascal.id, user_ids[0], "The current user, Pascal, should be the first in the result.")
        user_ids = [id_ for id_, __ in ResUsers.with_user(pascal).name_search('', limit=3)]
        self.assertEqual(pascal.id, user_ids[0], "The current user, Pascal, should be the first in the result.")
        self.assertEqual(len(user_ids), 3, "The number of results found should still respect the limit set.")
        jean_paul = self.users[1]
        user_ids = [id_ for id_, __ in ResUsers.with_user(jean_paul).name_search('Jean')]
        self.assertEqual(jean_paul.id, user_ids[0], "The current user, Jean-Paul, should be the first in the result")
        claude = self.users[4]
        user_ids = [id_ for id_, __ in ResUsers.with_user(claude).name_search('', limit=2)]
        self.assertEqual(claude.id, user_ids[0], "The current user, Claude, should be the first in the result.")
        self.assertNotEqual(claude.id, user_ids[1], "The current user, Claude, should not appear twice in the result")
        user_ids = [id_ for id_, __ in ResUsers.with_user(claude).name_search('', limit=5)]
        self.assertEqual(len(user_ids), len(set(user_ids)), "Some user(s), appear multiple times in the result")


@tagged('post_install', '-at_install')
class TestUserSettings(HttpCaseWithUserDemo):
    def test_user_group_settings(self):
        self.start_tour('/odoo/settings?debug=assets,tests', 'test_user_group_settings', login='admin')


@tagged('post_install', '-at_install')
class TestUserRoleGroupSync(HttpCaseWithUserDemo):
    """ Drives the real web client (not Form()/onchange()) to check that
    res.users' `role` <-> `group_ids` stay in sync in both directions:
    changing the "Role" radio must persist the regular-user marker group,
    and toggling a plain access-right group must be reflected back onto
    `role` (via _compute_role). This complements the pure-backend repro
    attempts in base/tests/test_res_users.py, which cannot catch a desync
    specific to the real widgets/dirty-tracking of the web client --
    Form()/onchange() always faithfully applies whatever the onchange
    returns, it doesn't simulate how the browser tracks/commits modified
    fields.

    debug mode is required in the URL: the "Extra Rights" section (groups
    without a privilege_id, where our test group lives) is only rendered
    when debug mode is active -- see ResUserGroupIdsField.setup() in
    res_user_group_ids_field.js (`this.debugMode.isActive() ? ... : ""`).
    """

    def setUp(self):
        super().setUp()
        self.extra_group = self.env['res.groups'].create({
            'name': 'Test Role Sync Extra Group',
        })
        # A 2nd company on the target user is the actual trigger condition
        # for the bug: UsersMultiCompany.new() only mutates group_ids when
        # company_count > 1 -- a single-company user never hits that code
        # path at all, so the tours below would pass identically with or
        # without the res_users.py fix unless the user has multiple
        # companies (matching the real-world report: Marc Demo has
        # company_count > 1).
        self.company2 = self.env['res.company'].create({'name': 'Role Sync Test Company 2'})
        self.test_user = self.env['res.users'].create({
            'name': 'Role Sync Test User',
            'login': 'role_sync_test_user',
            'group_ids': [Command.set(self.env.ref('base.group_user').ids)],
        })
        self.group_regular = self.env.ref('base.group_user_regular')
        # Give the user a 2nd company *without* going through write()/
        # create() (both have their own correct group_multi_company sync,
        # same idea as the new() override, so a plain write() here would
        # immediately self-correct group_ids and mask what we want to set
        # up: a user whose company_ids already say "multi-company" while
        # group_ids/role still say "light", matching Marc Demo's actual
        # starting state in the original bug report). This is exactly the
        # inconsistent starting state the bug needs to be observable.
        self.env.cr.execute(
            "INSERT INTO res_company_users_rel (cid, user_id) VALUES (%s, %s)",
            [self.company2.id, self.test_user.id],
        )
        self.test_user.invalidate_recordset()

    def _user_url(self):
        # Not /odoo/res.users/<id>: with hr installed, that bare model URL
        # resolves to the *simplified* HR form (base.view_users_simple_form,
        # no Access Rights notebook, no role field) instead of the real
        # Settings > Users form (base.view_users_form) that
        # base.action_res_users explicitly uses -- going through the
        # action's own path is what makes the correct view get picked.
        return f"/odoo/users/{self.test_user.id}?debug=1"

    def _assert_state(self, role, marker_expected, msg):
        self.test_user.invalidate_recordset()
        self.assertEqual(self.test_user.role, role, msg)
        if marker_expected:
            self.assertIn(self.group_regular, self.test_user.all_group_ids, msg)
        else:
            self.assertNotIn(self.group_regular, self.test_user.all_group_ids, msg)

    def test_role_toggle_with_intermediate_reload(self):
        """ regular -> save -> [reload] -> light -> save -> [reload] ->
        regular -> save -> [reload]. Starts with 'regular' since the test
        user is 'light_user' by default: setting light first would be a
        no-op (radio already selected, form never becomes dirty, no Save
        button to click) and wouldn't exercise anything. Each step is its
        own start_tour() call -- a fresh page load, i.e. a real reload --
        with a Python-side backend check between every single one. """
        self._assert_state('light_user', False, "initial state")

        self.start_tour(self._user_url(), 'role_sync_set_regular_and_save', login='admin')
        self._assert_state('regular_user', True, "after setting regular and saving")

        self.start_tour(self._user_url(), 'role_sync_reload_only', login='admin')
        self._assert_state(
            'regular_user', True,
            "after reload: role must still be 'regular_user' with the "
            "marker present -- this is the reported bug if it fails",
        )

        self.start_tour(self._user_url(), 'role_sync_set_light_and_save', login='admin')
        self._assert_state('light_user', False, "after setting light and saving")

        self.start_tour(self._user_url(), 'role_sync_reload_only', login='admin')
        self._assert_state('light_user', False, "after reload, still light")

        self.start_tour(self._user_url(), 'role_sync_set_regular_and_save', login='admin')
        self._assert_state('regular_user', True, "after setting regular and saving again")

        self.start_tour(self._user_url(), 'role_sync_reload_only', login='admin')
        self._assert_state(
            'regular_user', True,
            "after final reload: role must still be 'regular_user' with the "
            "marker present -- this is the reported bug if it fails",
        )

    def test_role_toggle_without_intermediate_reload(self):
        """ regular -> save -> light -> save -> regular -> save, all in ONE
        browser session (no reload in between), single reload only at the
        very end. Starts with 'regular' for the same reason as above: the
        test user is 'light_user' by default. """
        self._assert_state('light_user', False, "initial state")

        self.start_tour(
            self._user_url(), 'role_sync_regular_save_light_save_regular_save_no_reload', login='admin',
        )
        self._assert_state('regular_user', True, "after all toggles saved in one session")

        self.start_tour(self._user_url(), 'role_sync_reload_only', login='admin')
        self._assert_state(
            'regular_user', True,
            "after reload: role must still be 'regular_user' with the marker "
            "present -- this is the reported bug if it fails",
        )

    def test_role_toggle_reload_relies_on_autosave(self):
        """ light -> [no explicit Save] -> reload -> regular -> [no
        explicit Save] -> reload. Sanity check: an unsaved role change
        must not survive a reload (Odoo doesn't auto-save on unload). Not
        expected to reproduce the bug, but rules out a different save
        code path being involved. """
        self.start_tour(
            self._user_url(), 'role_sync_set_light_no_save_then_reload', login='admin',
        )
        self._assert_state(
            'light_user', False,
            "an unsaved role change must not persist across a reload",
        )

        self.start_tour(
            self._user_url(), 'role_sync_set_regular_no_save_then_reload', login='admin',
        )
        self._assert_state(
            'light_user', False,
            "an unsaved role change must not persist across a reload",
        )

    def test_extra_group_checkbox_drives_role_via_compute(self):
        """ group_ids -> role direction: checking a plain group (no
        privilege_id) directly must make `role` compute to 'regular_user'
        (_compute_role depends on group_ids), and this must survive a
        reload; unchecking it must bring `role` back to 'light_user'. """
        self._assert_state('light_user', False, "initial state")

        self.start_tour(
            self._user_url(), 'role_sync_check_extra_group_and_save', login='admin',
        )
        self._assert_state(
            'regular_user', True,
            "checking the extra-rights group must flip role to 'regular_user'",
        )

        self.start_tour(self._user_url(), 'role_sync_reload_only', login='admin')
        self._assert_state('regular_user', True, "role must survive the reload")

        self.start_tour(
            self._user_url(), 'role_sync_uncheck_extra_group_and_save', login='admin',
        )
        self._assert_state(
            'light_user', False,
            "unchecking the extra-rights group must flip role back to 'light_user'",
        )

        self.start_tour(self._user_url(), 'role_sync_reload_only', login='admin')
        self._assert_state('light_user', False, "role must survive the reload")
