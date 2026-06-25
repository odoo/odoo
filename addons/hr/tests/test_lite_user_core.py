# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install', 'lite_user_core')
class TestLiteUserCore(TransactionCase):
    """Core behaviour of the HR light-user feature.

    A Light user is not a separate kind of user: it is a regular internal user
    (``base.group_user``) whose extra privileges are limited to the minimal
    light set. There is no dedicated group and no dedicated ACL -- the ``role``
    field is a pure projection of group membership.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref('base.group_user')

    def test_provision_no_email_synthetic_login(self):
        emp = self.env['hr.employee'].create({'name': 'No Email'})
        self.assertTrue(emp.user_id, "an active employee must be provisioned with a user")
        self.assertTrue(emp.user_id.login.startswith('__emp_'),
                        "a userless, emailless employee gets a synthetic login")
        self.assertFalse(emp.user_id.share, "the provisioned user is an internal user")
        self.assertIn(self.group_user, emp.user_id.all_group_ids,
                      "a Light user is a regular internal user")
        self.assertEqual(emp.user_id.role, 'light',
                         "with no extra access, the provisioned user is a Light user")

    def test_provision_no_email_logins_are_unique(self):
        """Several emailless employees each get a distinct synthetic login, even
        in a non-default company (the login sequence must be company-global)."""
        company = self.env['res.company'].create({'name': 'Other Co'})
        emps = self.env['hr.employee'].with_company(company).create([
            {'name': 'No Email A'}, {'name': 'No Email B'}])
        logins = emps.user_id.mapped('login')
        self.assertEqual(len(set(logins)), 2, "synthetic logins must be unique")
        self.assertNotIn('__emp_False', logins,
                         "the synthetic login sequence must resolve in any company")

    def test_provision_with_email(self):
        emp = self.env['hr.employee'].create({'name': 'Mailed', 'work_email': 'mailed@example.com'})
        self.assertEqual(emp.user_id.login, 'mailed@example.com')

    def test_provision_reuses_existing_user(self):
        user = self.env['res.users'].create({
            'name': 'Reuse', 'login': 'reuse@example.com',
            'group_ids': [(6, 0, self.group_user.ids)],
        })
        emp = self.env['hr.employee'].create({'name': 'Reuse Emp', 'work_email': 'reuse@example.com'})
        self.assertEqual(emp.user_id, user, "an existing user matching the email is reused, not duplicated")

    def test_active_requires_user_constraint(self):
        with self.assertRaises(ValidationError):
            emp = self.env['hr.employee'].create({'name': 'Headless'})
            emp.user_id = False

    def test_inactive_employee_needs_no_user(self):
        emp = self.env['hr.employee'].create({'name': 'Ghost', 'active': False})
        emp.user_id = False
        self.assertFalse(emp.user_id)

    def test_role_projection(self):
        """``role`` reflects group membership: light / user / administrator."""
        admin = self.env.ref('base.user_admin')
        self.assertEqual(admin.role, 'group_system')
        light = self.env['hr.employee'].create({'name': 'Light'}).user_id
        self.assertEqual(light.role, 'light')

    def test_real_access_makes_regular(self):
        """Granting access beyond the light set turns a Light user into a regular
        User -- the projection follows from the user gaining an extra app group."""
        user = self.env['hr.employee'].create({'name': 'Climber'}).user_id
        self.assertEqual(user.role, 'light')
        app_group = self.env['res.groups'].create({
            'name': 'Some App / User',
            'implied_ids': [(4, self.group_user.id)],
        })
        user.write({'group_ids': [(4, app_group.id)]})
        self.assertIn(self.group_user, user.all_group_ids)
        self.assertEqual(user.role, 'group_user')

    def test_role_inverse_demote_to_light(self):
        """Writing role='light' is lossy: it strips every extra app group down to
        the internal baseline."""
        user = self.env['hr.employee'].create({'name': 'Demote'}).user_id
        app_group = self.env['res.groups'].create({
            'name': 'Some App / User',
            'implied_ids': [(4, self.group_user.id)],
        })
        user.write({'group_ids': [(4, app_group.id)]})
        self.assertEqual(user.role, 'group_user')
        user.write({'role': 'light'})
        self.assertEqual(user.role, 'light')
        self.assertNotIn(app_group, user.group_ids,
                         "demoting to Light removes the extra app access")
        self.assertIn(self.group_user, user.group_ids)

    def test_role_inverse_promote_to_admin(self):
        """Writing role='group_system' keeps app groups and adds the admin anchor."""
        user = self.env['hr.employee'].create({'name': 'Boss'}).user_id
        user.write({'role': 'group_system'})
        self.assertEqual(user.role, 'group_system')
        self.assertTrue(user.has_group('base.group_system'))

    def test_lite_user_can_browse_directory(self):
        """A Light user (a plain internal user) can read the employee directory
        and the models its views depend on."""
        light_user = self.env['hr.employee'].create({'name': 'Browser'}).user_id
        for model in ('hr.employee.public', 'hr.department', 'hr.job',
                      'hr.work.location', 'hr.employee.category'):
            # must not raise AccessError
            self.env[model].with_user(light_user).check_access('read')

    def test_lite_user_can_load_backend(self):
        """A provisioned Light user can load the web client: menus and its own
        user/groups must be readable."""
        light_user = self.env['hr.employee'].create({'name': 'Backend'}).user_id
        # the real path the web client uses to render the menu tree
        self.env['ir.ui.menu'].with_user(light_user).load_menus(False)
        # reading own user record with its groups (user preferences)
        light_user.with_user(light_user).read(['name', 'login', 'group_ids'])
