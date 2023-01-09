# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.models.res_users import is_selection_groups, get_selection_groups, name_selection_groups
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, Form, tagged, new_test_user
from odoo.tools import mute_logger


class TestUsers(TransactionCase):

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
        user_internal = self.env['res.users'].create({
            'name': 'Internal',
            'login': 'user_internal',
            'password': 'password',
            'groups_id': [self.env.ref('base.group_user').id],
        })

        with self.assertRaises(UserError, msg='Internal users should not be able to deactivate their account'):
            user_internal._deactivate_portal_user()

    @mute_logger('odoo.sql_db')
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
            'groups_id': [self.env.ref('base.group_portal').id],
        })
        portal_partner = portal_user.partner_id

        portal_user_2 = User.create({
            'name': 'Portal',
            'login': 'portal_user_2',
            'password': 'password',
            'groups_id': [self.env.ref('base.group_portal').id],
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

        self.env['res.users.deletion']._gc_portal_users()

        self.assertFalse(portal_user.exists(), 'Should have removed the user')
        self.assertFalse(portal_partner.exists(), 'Should have removed the partner')
        self.assertEqual(asked_deletion_1.state, 'done', 'Should have marked the deletion as done')

        self.assertTrue(portal_user_2.exists(), 'Should have kept the user')
        self.assertTrue(portal_partner_2.exists(), 'Should have kept the partner')
        self.assertEqual(asked_deletion_2.state, 'fail', 'Should have marked the deletion as failed')

    def test_context_get_lang_false(self):
        user = new_test_user(self.env, 'jackoneill')
        user = user.with_user(user)

        self.assertEqual(user.context_get()['lang'], 'en_US')

        user.lang = False
        self.assertEqual(user.context_get()['lang'], 'en_US')


@tagged('post_install', '-at_install')
class TestUsers2(TransactionCase):

    def test_reified_groups(self):
        """ The groups handler doesn't use the "real" view with pseudo-fields
        during installation, so it always works (because it uses the normal
        groups_id field).
        """
        # use the specific views which has the pseudo-fields
        f = Form(self.env['res.users'], view='base.view_users_form')
        f.name = "bob"
        f.login = "bob"
        user = f.save()

        self.assertIn(self.env.ref('base.group_user'), user.groups_id)

    def test_selection_groups(self):
        # create 3 groups that should be in a selection
        app = self.env['ir.module.category'].create({'name': 'Foo'})
        group1, group2, group0 = self.env['res.groups'].create([
            {'name': name, 'category_id': app.id}
            for name in ('User', 'Manager', 'Visitor')
        ])
        # THIS PART IS NECESSARY TO REPRODUCE AN ISSUE: group1.id < group2.id < group0.id
        self.assertLess(group1.id, group2.id)
        self.assertLess(group2.id, group0.id)
        # implication order is group0 < group1 < group2
        group2.implied_ids = group1
        group1.implied_ids = group0
        groups = group0 + group1 + group2

        # determine the name of the field corresponding to groups
        fname = next(
            name
            for name in self.env['res.users'].fields_get()
            if is_selection_groups(name) and group0.id in get_selection_groups(name)
        )
        self.assertCountEqual(get_selection_groups(fname), groups.ids)

        # create a user
        user = self.env['res.users'].create({'name': 'foo', 'login': 'foo'})

        # put user in group0, and check field value
        user.write({fname: group0.id})
        self.assertEqual(user.groups_id & groups, group0)
        self.assertEqual(user.read([fname])[0][fname], group0.id)

        # put user in group1, and check field value
        user.write({fname: group1.id})
        self.assertEqual(user.groups_id & groups, group0 + group1)
        self.assertEqual(user.read([fname])[0][fname], group1.id)

        # put user in group2, and check field value
        user.write({fname: group2.id})
        self.assertEqual(user.groups_id & groups, groups)
        self.assertEqual(user.read([fname])[0][fname], group2.id)

    def test_read_group_with_reified_field(self):
        """ Check that read_group gets rid of reified fields"""
        User = self.env['res.users']
        fnames = ['name', 'email', 'login']

        # find some reified field name
        reified_fname = next(
            fname
            for fname in User.fields_get()
            if fname.startswith(('in_group_', 'sel_groups_'))
        )

        # check that the reified field name has no effect in fields
        res_with_reified = User.read_group([], fnames + [reified_fname], ['company_id'])
        res_without_reified = User.read_group([], fnames, ['company_id'])
        self.assertEqual(res_with_reified, res_without_reified, "Reified fields should be ignored")

        # Verify that the read_group is raising an error if reified field is used as groupby
        with self.assertRaises(ValueError):
            User.read_group([], fnames + [reified_fname], [reified_fname])

    def test_reified_groups_on_change(self):
        """Test that a change on a reified fields trigger the onchange of groups_id."""
        group_public = self.env.ref('base.group_public')
        group_portal = self.env.ref('base.group_portal')
        group_user = self.env.ref('base.group_user')

        # Build the reified group field name
        user_groups = group_public | group_portal | group_user
        user_groups_ids = [str(group_id) for group_id in sorted(user_groups.ids)]
        group_field_name = f"sel_groups_{'_'.join(user_groups_ids)}"

        # <group col="4" attrs="{'invisible': [('sel_groups_1_9_10', '!=', 1)]}" groups="base.group_no_one" class="o_label_nowrap">
        with self.debug_mode():
            user_form = Form(self.env['res.users'], view='base.view_users_form')
        user_form.name = "Test"
        user_form.login = "Test"
        self.assertFalse(user_form.share)

        setattr(user_form, group_field_name, group_portal.id)
        self.assertTrue(user_form.share, 'The groups_id onchange should have been triggered')

        setattr(user_form, group_field_name, group_user.id)
        self.assertFalse(user_form.share, 'The groups_id onchange should have been triggered')

        setattr(user_form, group_field_name, group_public.id)
        self.assertTrue(user_form.share, 'The groups_id onchange should have been triggered')


@tagged('post_install', '-at_install', 'res_groups')
class TestUsersGroupWarning(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """
            These are the Groups and their Hierarchy we have Used to test Group warnings.

            Category groups hierarchy:
                Sales
                ├── User: All Documents
                └── Administrator
                Timesheets
                ├── User: own timesheets only
                ├── User: all timesheets
                └── Administrator
                Project
                ├── User
                └── Administrator
                Field Service
                ├── User
                └── Administrator

            Implied groups hierarchy:
                Sales / Administrator
                └── Sales / User: All Documents

                Timesheets / Administrator
                └── Timesheets / User: all timesheets
                    └── Timehseets / User: own timesheets only

                Project / Administrator
                ├── Project / User
                └── Timesheets / User: all timesheets

                Field Service / Administrator
                ├── Sales / Administrator
                ├── Project / Administrator
                └── Field Service / User
        """
        super().setUpClass()
        ResGroups = cls.env['res.groups']
        IrModuleCategory = cls.env['ir.module.category']
        categ_sales = IrModuleCategory.create({'name': 'Sales'})
        categ_project = IrModuleCategory.create({'name': 'Project'})
        categ_field_service = IrModuleCategory.create({'name': 'Field Service'})
        categ_timesheets = IrModuleCategory.create({'name': 'Timesheets'})

        # Sales
        cls.group_sales_user, cls.group_sales_administrator = ResGroups.create([
            {'name': 'User: All Documents', 'category_id': categ_sales.id},
            {'name': 'Administrator', 'category_id': categ_sales.id},
        ])
        cls.sales_categ_field = name_selection_groups((cls.group_sales_user | cls.group_sales_administrator).ids)
        cls.group_sales_administrator.implied_ids = cls.group_sales_user

        # Timesheets
        cls.group_timesheets_user_own_timesheet = ResGroups.create([
            {'name': 'User: own timesheets only', 'category_id': categ_timesheets.id}
        ])
        cls.group_timesheets_user_all_timesheet = ResGroups.create([
            {'name': 'User: all timesheets', 'category_id': categ_timesheets.id}
        ])
        cls.group_timesheets_administrator = ResGroups.create([
            {'name': 'Administrator', 'category_id': categ_timesheets.id}
        ])
        cls.timesheets_categ_field = name_selection_groups((cls.group_timesheets_user_own_timesheet |
                                                            cls.group_timesheets_user_all_timesheet |
                                                            cls.group_timesheets_administrator).ids
                                                           )
        cls.group_timesheets_administrator.implied_ids += cls.group_timesheets_user_all_timesheet
        cls.group_timesheets_user_all_timesheet.implied_ids += cls.group_timesheets_user_own_timesheet

        # Project
        cls.group_project_user, cls.group_project_admnistrator = ResGroups.create([
            {'name': 'User', 'category_id': categ_project.id},
            {'name': 'Administrator', 'category_id': categ_project.id},
        ])
        cls.project_categ_field = name_selection_groups((cls.group_project_user | cls.group_project_admnistrator).ids)
        cls.group_project_admnistrator.implied_ids = (cls.group_project_user | cls.group_timesheets_user_all_timesheet)

        # Field Service
        cls.group_field_service_user, cls.group_field_service_administrator = ResGroups.create([
            {'name': 'User', 'category_id': categ_field_service.id},
            {'name': 'Administrator', 'category_id': categ_field_service.id},
        ])
        cls.field_service_categ_field = name_selection_groups((cls.group_field_service_user | cls.group_field_service_administrator).ids)
        cls.group_field_service_administrator.implied_ids = (cls.group_sales_administrator |
                                                             cls.group_project_admnistrator |
                                                             cls.group_field_service_user).ids

        # User
        cls.test_group_user = cls.env['res.users'].create({
            'name': 'Test Group User',
            'login': 'TestGroupUser',
            'groups_id': (
                cls.env.ref('base.group_user') |
                cls.group_timesheets_administrator |
                cls.group_field_service_administrator).ids,
        })


    def test_user_group_empty_group_warning(self):
        """ User changes Empty Sales access from 'Sales: Administrator'. The
        warning should be there since 'Sales: Administrator' is required when
        user is having 'Field Service: Administrator'. When user reverts the
        changes, warning should disappear. """
        # 97 requests if only base is installed
        # 412 runbot community
        # 549 runbot enterprise
        with self.assertQueryCount(__system__=549), \
             Form(self.test_group_user.with_context(show_user_group_warning=True), view='base.view_users_form') as UserForm:
            UserForm._values[self.sales_categ_field] = False
            UserForm._perform_onchange([self.sales_categ_field])

            self.assertEqual(
                UserForm.user_group_warning,
                'Since Test Group User is a/an "Field Service: Administrator", they will at least obtain the right "Sales: Administrator"'
            )

            UserForm._values[self.sales_categ_field] = self.group_sales_administrator.id
            UserForm._perform_onchange([self.sales_categ_field])
            self.assertFalse(UserForm.user_group_warning)

    def test_user_group_inheritance_warning(self):
        """ User changes 'Sales: User' from 'Sales: Administrator'. The warning
        should be there since 'Sales: Administrator' is required when user is
        having 'Field Service: Administrator'. When user reverts the changes,
        warning should disappear. """
        # 97 requests if only base is installed
        # 412 runbot community
        # 549 runbot enterprise
        with self.assertQueryCount(__system__=549), \
             Form(self.test_group_user.with_context(show_user_group_warning=True), view='base.view_users_form') as UserForm:
            UserForm._values[self.sales_categ_field] = self.group_sales_user.id
            UserForm._perform_onchange([self.sales_categ_field])

            self.assertEqual(
                UserForm.user_group_warning,
                'Since Test Group User is a/an "Field Service: Administrator", they will at least obtain the right "Sales: Administrator"'
            )

            UserForm._values[self.sales_categ_field] = self.group_sales_administrator.id
            UserForm._perform_onchange([self.sales_categ_field])
            self.assertFalse(UserForm.user_group_warning)

    def test_user_group_inheritance_warning_multi(self):
        """ User changes 'Sales: User' from 'Sales: Administrator' and
        'Project: User' from 'Project: Administrator'. The warning should
        be there since 'Sales: Administrator' and 'Project: Administrator'
        are required when user is havning 'Field Service: Administrator'.
        When user reverts the changes For 'Sales: Administrator', warning
        should disappear for Sales Access."""
        # 101 requests if only base is installed
        # 416 runbot community
        # 553 runbot enterprise
        with self.assertQueryCount(__system__=553), \
             Form(self.test_group_user.with_context(show_user_group_warning=True), view='base.view_users_form') as UserForm:
            UserForm._values[self.sales_categ_field] = self.group_sales_user.id
            UserForm._values[self.project_categ_field] = self.group_project_user.id
            UserForm._perform_onchange([self.sales_categ_field])

            self.assertTrue(
                UserForm.user_group_warning,
                'Since Test Group User is a/an "Field Service: Administrator", they will at least obtain the right "Sales: Administrator", Project: Administrator"',
            )

            UserForm._values[self.sales_categ_field] = self.group_sales_administrator.id
            UserForm._perform_onchange([self.sales_categ_field])

            self.assertEqual(
                UserForm.user_group_warning,
                'Since Test Group User is a/an "Field Service: Administrator", they will at least obtain the right "Project: Administrator"'
            )

    def test_user_group_least_possible_inheritance_warning(self):
        """ User changes 'Timesheets: User: own timesheets only ' from
        'Timesheets: Administrator'. The warning should be there since
        'Timesheets: User: all timesheets' is at least required when user is
        having 'Project: Administrator'. When user reverts the changes For
        'Timesheets: User: all timesheets', warning should disappear."""
        # 98 requests if only base is installed
        # 413 runbot community
        # 550 runbot enterprise
        with self.assertQueryCount(__system__=550), \
             Form(self.test_group_user.with_context(show_user_group_warning=True), view='base.view_users_form') as UserForm:
            UserForm._values[self.timesheets_categ_field] = self.group_timesheets_user_own_timesheet.id
            UserForm._perform_onchange([self.timesheets_categ_field])

            self.assertEqual(
                UserForm.user_group_warning,
                'Since Test Group User is a/an "Project: Administrator", they will at least obtain the right "Timesheets: User: all timesheets"'
            )

            UserForm._values[self.timesheets_categ_field] = self.group_timesheets_user_all_timesheet.id
            UserForm._perform_onchange([self.timesheets_categ_field])
            self.assertFalse(UserForm.user_group_warning)

    def test_user_group_parent_inheritance_no_warning(self):
        """ User changes 'Field Service: User' from 'Field Service: Administrator'.
        The warning should not be there since 'Field Service: User' is not affected
        by any other groups."""
        # 83 requests if only base is installed
        # 397 runbot community
        # 534 runbot enterprise
        with self.assertQueryCount(__system__=534), \
             Form(self.test_group_user.with_context(show_user_group_warning=True), view='base.view_users_form') as UserForm:
            UserForm._values[self.field_service_categ_field] = self.group_field_service_user.id
            UserForm._perform_onchange([self.field_service_categ_field])

            self.assertFalse(UserForm.user_group_warning)
