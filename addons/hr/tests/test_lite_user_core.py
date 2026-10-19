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
        cls.group_user_light = cls.env.ref('base.group_user')

    def test_provision_with_email(self):
        emp = self.env['hr.employee'].create({'name': 'Mailed', 'work_email': 'mailed@example.com'})
        emp.user_id = emp._get_or_create_light_user()
        self.assertEqual(emp.user_id.login, 'mailed@example.com')

    def test_provision_reuses_existing_user(self):
        user = self.env['res.users'].create({
            'name': 'Reuse', 'login': 'reuse@example.com',
            'group_ids': [(6, 0, self.group_user_light.ids)],
        })
        emp = self.env['hr.employee'].create({'name': 'Reuse Emp', 'work_email': 'reuse@example.com'})
        emp.user_id = emp._get_or_create_light_user()
        self.assertEqual(emp.user_id, user, "an existing user matching the email is reused, not duplicated")

    def test_inactive_employee_needs_no_user(self):
        # here we don't even try to create.
        emp = self.env['hr.employee'].create({'name': 'Ghost', 'active': False})
        self.assertFalse(emp.user_id)

    def test_employee_without_email_leads_to_no_user(self):
        # here, we try but as default is to make user not required, no user is created when missing email.
        # Should fail when forcing to create user as missing email.
        # Should not fail nor create user when retrying with 'required'.
        emp = self.env['hr.employee'].create({'name': 'Ghost'})
        self.assertFalse(emp.user_id)
        with self.assertRaises(ValidationError):
            emp.user_id = emp._get_or_create_light_user()
        emp.work_email = 'ghost@ghost.com'
        emp.user_id = emp._get_or_create_light_user()
        self.assertEqual(emp.user_id.login, 'ghost@ghost.com')

    def test_real_access_makes_regular(self):
        """Granting access beyond the light set turns a Light user into a regular
        User -- the projection follows from the user gaining an extra app group."""
        emp = self.env['hr.employee'].create({'name': 'Climber', 'work_email': 'climber@employee.com'})
        emp.user_id = emp._get_or_create_light_user()
        self.assertEqual(emp.user_id.role, 'light_user')
        app_group = self.env['res.groups'].create({
            'name': 'Some App / User',
            'implied_ids': [(4, self.group_user_light.id)],
        })
        emp.user_id.write({'group_ids': [(4, app_group.id)]})
        self.assertIn(self.group_user_light, emp.user_id.all_group_ids)
        self.assertEqual(emp.user_id.role, 'regular_user')

    def test_lite_user_can_browse_directory(self):
        """A Light user (a plain internal user) can read the employee directory
        and the models its views depend on."""
        light_user = self.env['hr.employee'].create({'name': 'Browser', 'work_email': 'browser@employee.com'}).user_id
        for model in ('hr.employee.public', 'hr.department', 'hr.job',
                      'hr.work.location', 'hr.employee.category'):
            # must not raise AccessError
            self.env[model].with_user(light_user).check_access('read')

    def test_lite_user_can_load_backend(self):
        """A provisioned Light user can load the web client: menus and its own
        user/groups must be readable."""
        light_user = self.env['hr.employee'].create({'name': 'Backend', 'work_email': 'backend@employee.com'}).user_id
        # the real path the web client uses to render the menu tree
        self.env['ir.ui.menu'].with_user(light_user).load_menus(False)
        # reading own user record with its groups (user preferences)
        light_user.with_user(light_user).read(['name', 'login', 'group_ids'])
