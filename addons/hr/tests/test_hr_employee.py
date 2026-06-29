# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from psycopg2.errors import UniqueViolation
from freezegun import freeze_time

from odoo import fields, Command
from odoo.addons.phone_validation.tools import phone_validation
from odoo.fields import Domain
from odoo.tests import Form, users, new_test_user, HttpCase, tagged, TransactionCase
from odoo.addons.hr.tests.common import TestHrCommon
from odoo.tools import mute_logger
from odoo.exceptions import ValidationError, AccessError
from psycopg2.errors import NotNullViolation


@tagged('at_install', '-post_install')  # LEGACY at_install, fails post install
class TestHrEmployee(TestHrCommon):

    def setUp(self):
        super().setUp()
        self.user_without_image = self.env['res.users'].create({
            'name': 'Marc Demo',
            'email': 'mark.brown23@example.com',
            'image_1920': False,
            'login': 'demo_1',
            'password': 'demo_123'
        })
        self.employee_without_image = self.env['hr.employee'].create({
            'user_id': self.user_without_image.id,
            'image_1920': False
        })

    def test_employee_must_have_active_version(self):
        employee = self.env['hr.employee'].create({
            'name': 'Batman'
        })
        self.assertEqual(len(employee.version_ids), 1)
        employee_version = employee.version_id
        with self.assertRaises(ValidationError, msg="An employee should always have a version"):
            employee.write({'version_ids': False})
        with self.assertRaises(ValidationError, msg="An employee should always have a version"):
            employee_version.unlink()
        with self.assertRaises(ValidationError, msg="An employee should always have a version"):
            employee_version.write({
                'employee_id': self.employee_without_image.id
            })
        with self.assertRaises(ValidationError, msg="An employee should always have an active version"):
            employee_version.write({'active': False})

    def test_employee_smart_button_multi_company(self):
        partner = self.env['res.partner'].create({'name': 'Partner Test'})
        company_A = self.env['res.company'].create({'name': 'company_A'})
        company_B = self.env['res.company'].create({'name': 'company_B'})
        self.env['hr.employee'].create({
            'name': 'employee_A',
            'work_contact_id': partner.id,
            'company_id': company_A.id,
        })
        self.env['hr.employee'].create({
            'name': 'employee_B',
            'work_contact_id': partner.id,
            'company_id': company_B.id
        })

        partner.with_context(allowed_company_ids=[company_A.id])._compute_employees_count()
        self.assertEqual(partner.employees_count, 1)
        partner.with_context(allowed_company_ids=[company_B.id])._compute_employees_count()
        self.assertEqual(partner.employees_count, 1)
        single_company_action = partner.with_context(allowed_company_ids=[company_B.id]).action_open_employees()
        self.assertEqual(single_company_action.get('view_mode'), 'form')
        partner.with_context(allowed_company_ids=[company_A.id, company_B.id])._compute_employees_count()
        self.assertEqual(partner.employees_count, 2)
        multi_company_action = partner.with_context(allowed_company_ids=[company_A.id, company_B.id]).action_open_employees()
        self.assertEqual(multi_company_action.get('view_mode'), 'kanban')

    def test_employee_linked_partner(self):
        user_partner = self.user_without_image.partner_id
        work_contact = self.employee_without_image.work_contact_id
        self.assertEqual(user_partner, work_contact)

    def test_employee_resource(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_officer.company_id.tz = _tz
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer).with_context({'tz': 'Europe/Brussels'})
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee = employee_form.save()
        self.assertEqual(employee.tz, 'Europe/Brussels')

    def test_compute_user_company_employee(self):
        test_user = new_test_user(self.env, login='test_user', groups='base.group_user', name='testuser', email='test@user.com')
        test_user.action_create_employee()
        employee = test_user.employee_id
        multiple_users = self.user_without_image + test_user

        multiple_users.invalidate_recordset(['employee_id'])

        multiple_users.with_user(test_user).employee_id  # trigger the compute in batch and in non-sudo

        self.assertEqual(test_user.with_user(test_user).employee_id, employee)
        self.assertEqual(test_user.with_user(test_user).sudo().employee_id, employee)

    def test_employee_timezone(self):
        self.res_users_hr_officer.tz = "Africa/Cairo"
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.user_id = self.res_users_hr_officer
        employee_form.name = 'Youssef Ahmed'
        employee_form.work_email = 'yoahm@example.com'
        employee = employee_form.save()

        # validate timezone sync between employee & user
        self.assertEqual(employee.tz, self.res_users_hr_officer.tz)

        # validate that we can change timezone on user
        self.res_users_hr_officer.tz = "Europe/Brussels"
        self.assertEqual(self.res_users_hr_officer.tz, employee.tz)

        # validate that we can change timezone on employee
        employee.tz = "Europe/London"
        self.assertEqual(self.res_users_hr_officer.tz, employee.tz)

        # Check False value on employee
        with mute_logger('odoo.sql_db'), self.assertRaises(NotNullViolation):
            employee.tz = False

        # Check False value on user
        with mute_logger('odoo.sql_db'), self.assertRaises(NotNullViolation):
            self.res_users_hr_officer.tz = False

    def test_employee_from_user(self):
        _tz = 'Pacific/Apia'
        _tz2 = 'America/Tijuana'
        self.res_users_hr_officer.company_id.tz = _tz
        self.res_users_hr_officer.tz = _tz2
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee_form.user_id = self.res_users_hr_officer
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, self.res_users_hr_officer.email)
        self.assertEqual(employee.tz, self.res_users_hr_officer.tz)

    def test_employee_computed_from_user(self):
        self.res_users_hr_officer.name = 'Raoul Grosbedon'
        self.res_users_hr_officer.email = 'raoul@example.com'
        Employee = self.env['hr.employee']
        employee_form = Form(Employee)
        employee_form.user_id = self.res_users_hr_officer
        self.assertEqual(employee_form.name, 'Raoul Grosbedon')
        self.assertEqual(employee_form.work_email, 'raoul@example.com')
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, 'raoul@example.com')

    def test_employee_from_manager_tz_no_reset(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_manager.tz = False
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_manager)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee_form.tz = _tz
        employee_form.user_id = self.res_users_hr_manager
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, self.res_users_hr_manager.email)
        self.assertEqual(employee.tz, _tz)

    def test_employee_has_avatar_even_if_it_has_no_image(self):
        self.assertTrue(self.employee_without_image.avatar_128)
        self.assertTrue(self.employee_without_image.avatar_256)
        self.assertTrue(self.employee_without_image.avatar_512)
        self.assertTrue(self.employee_without_image.avatar_1024)
        self.assertTrue(self.employee_without_image.avatar_1920)

    def test_employee_has_same_avatar_as_corresponding_user(self):
        self.assertEqual(self.employee_without_image.avatar_1920.content, self.user_without_image.avatar_1920.content)

    def test_employee_member_of_department(self):
        dept, dept_sub, dept_sub_sub, dept_other, dept_parent = self.env['hr.department'].create([
            {
                'name': 'main',
            },
            {
                'name': 'sub',
            },
            {
                'name': 'sub-sub',
            },
            {
                'name': 'other',
            },
            {
                'name': 'parent',
            },
        ])
        dept_sub.parent_id = dept
        dept_sub_sub.parent_id = dept_sub
        dept.parent_id = dept_parent
        emp, emp_sub, emp_sub_sub, emp_other, emp_parent = self.env['hr.employee'].with_user(self.res_users_hr_officer).create([
            {
                'name': 'employee',
                'department_id': dept.id,
            },
            {
                'name': 'employee sub',
                'department_id': dept_sub.id,
            },
            {
                'name': 'employee sub sub',
                'department_id': dept_sub_sub.id,
            },
            {
                'name': 'employee other',
                'department_id': dept_other.id,
            },
            {
                'name': 'employee parent',
                'department_id': dept_parent.id,
            },
        ])
        self.res_users_hr_officer.employee_ids = emp
        self.assertTrue(emp.member_of_department)
        self.assertTrue(emp_sub.member_of_department)
        self.assertTrue(emp_sub_sub.member_of_department)
        self.assertFalse(emp_other.member_of_department)
        self.assertFalse(emp_parent.member_of_department)
        employees = emp + emp_sub + emp_sub_sub + emp_other + emp_parent
        self.assertEqual(
            employees.filtered_domain(employees.version_id._search_part_of_department('in', [True])),
            emp + emp_sub + emp_sub_sub)
        self.assertEqual(
            employees.filtered_domain(['!'] + employees.version_id._search_part_of_department('in', [True])),
            emp_other + emp_parent)

    def test_employee_create_from_user(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test User 3 - employee'
        })
        user_1, user_2, user_3 = self.env['res.users'].create([
            {
                'name': 'Test User',
                'login': 'test_user',
                'email': 'test_user@odoo.com',
            },
            {
                'name': 'Test User 2',
                'login': 'test_user_2',
                'email': 'test_user_2@odoo.com',
                'create_employee': True,
            },
            {
                'name': 'Test User 3',
                'login': 'test_user_3',
                'email': 'test_user_3@odoo.com',
                'create_employee_id': employee.id,
            },
        ])
        # Test that creating an user does not create an employee by default
        self.assertFalse(user_1.employee_id)
        # Test that setting create_employee does create the associated employee
        self.assertTrue(user_2.employee_id)
        # Test that creating an user with a given employee associates the employee correctly
        self.assertEqual(user_3.employee_id, employee)

    def test_employee_create_from_signup(self):
        # Test that an employee is not created when signin up on the website
        partner = self.env['res.partner'].create({
            'name': 'test partner'
        })
        self.env['res.users'].signup({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test_user@odoo.com',
            'password': 'test_user_password',
            'partner_id': partner.id,
        })
        self.assertFalse(self.env['res.users'].search([('login', '=', 'test_user')]).employee_id)

    def test_availability_user_infos_employee(self):
        """ Ensure that all the user infos needed to display the avatar popover card
            are available on the model hr.employee.
        """
        user = self.env['res.users'].create([{
            'name': 'Test user',
            'login': 'test',
            'email': 'test@odoo.perso',
            'phone': '+32488990011',
        }])
        employee = self.env['hr.employee'].create([{
            'name': 'Test employee',
            'user_id': user.id,
        }])
        user_fields = ['email', 'phone']
        for field in user_fields:
            self.assertEqual(employee[field], user[field])

    def test_set_user_on_new_employee(self):
        test_company = self.env['res.company'].create({
            'name': 'Test User Company',
        })
        self.env['hr.employee'].create({
            'name': 'Hr Officer - employee',
            'user_id': self.res_users_hr_officer.id,
            'company_id': test_company.id,
        })

        self.res_users_hr_officer.write({'company_ids': test_company.ids, 'company_id': test_company.id})

        # Try to set the user with existing employee in the company, on a new employee form
        employee_form = Form(self.env['hr.employee'].with_user(self.res_users_hr_officer).with_company(company=test_company.id))
        employee_form.name = "Second employee"
        employee_form.user_id = self.res_users_hr_officer
        with mute_logger('odoo.sql_db'), self.assertRaises(UniqueViolation), self.assertRaises(ValidationError):
            employee_form.save()

        employee_2 = self.env['hr.employee'].create({
            'name': 'Hr 2 - employee',
            'company_id': test_company.id,
        })

        # Try to set the user with existing employee in the company, on another existing employee
        employee_2_form = Form(employee_2.with_user(self.res_users_hr_officer).with_company(company=test_company.id))
        employee_2_form.user_id = self.res_users_hr_officer
        with mute_logger('odoo.sql_db'), self.assertRaises(UniqueViolation), self.assertRaises(ValidationError):
            employee_2_form.save()


    @users('admin')
    def test_change_user_on_employee(self):
        test_other_user = self.env['res.users'].create({
            'name': 'Test Other User',
            'login': 'test_other_user',
        })
        test_other_user.partner_id.company_id = self.env.company
        test_company = self.env['res.company'].create({
            'name' : 'Test User Company',
        })
        self.env.user.write({'company_ids': test_company.ids, 'company_id': test_company.id})
        test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
        })
        test_user.partner_id.company_id = test_company
        bank_account = self.env['res.partner.bank'].create({
            'account_number': '1234567',
            'partner_id' : test_user.partner_id.id,
        })
        test_employee = self.env['hr.employee'].create({
            'name': 'Test User - employee',
            'user_id': test_user.id,
            'company_id': test_company.id,
            'bank_account_ids': [Command.link(bank_account.id)],
        })
        # change user -> bank account change company
        with Form(test_employee) as employee_form:
            employee_form.user_id = test_other_user
        # change user back -> check that there is no company error
        with Form(test_employee) as employee_form:
            employee_form.user_id = test_user

    def test_user_backs_one_employee_per_company(self):
        """A single user can back one employee in each company it belongs to."""
        company_A = self.env['res.company'].create({'name': 'company_A'})
        company_B = self.env['res.company'].create({'name': 'company_B'})
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
        })
        employee_A = self.env['hr.employee'].create({
            'name': 'employee_A',
            'user_id': user.id,
            'company_id': company_A.id,
        })
        employee_B = self.env['hr.employee'].create({
            'name': 'employee_B',
            'user_id': user.id,
            'company_id': company_B.id,
        })
        # the same user backs one employee in each company
        self.assertEqual(user.with_company(company_A).employee_id, employee_A)
        self.assertEqual(user.with_company(company_B).employee_id, employee_B)
        self.assertEqual(user.partner_id.with_context(active_test=False).employee_ids,
                         employee_A + employee_B)

    def test_avatar(self):
        # Check simple employee has a generated image (initials)
        employee_georgette = self.env['hr.employee'].create({'name': 'Georgette Pudubec'})
        self.assertTrue(employee_georgette.image_1920)
        self.assertTrue(employee_georgette.avatar_1920)

        self.assertTrue(employee_georgette.work_contact_id)
        self.assertTrue(employee_georgette.work_contact_id.image_1920)
        self.assertTrue(employee_georgette.work_contact_id.avatar_1920)

        # Check user has a generate image
        user_norbert = self.env['res.users'].create({'name': 'Norbert Comidofisse', 'login': 'Norbert6870'})
        self.assertTrue(user_norbert.image_1920)
        self.assertTrue(user_norbert.avatar_1920)

        # Check that linked employee got user image
        employee_norbert = self.env['hr.employee'].create({'name': 'Norbert Employee', 'user_id': user_norbert.id})
        self.assertEqual(employee_norbert.image_1920.content, user_norbert.image_1920.content)
        self.assertEqual(employee_norbert.avatar_1920.content, user_norbert.avatar_1920.content)

    def test_badge_validation(self):
        # check employee's barcode should be a sequence of digits and alphabets
        employee = self.env['hr.employee'].create({
            'name': 'Badge Employee'
        })

        employee_form = Form(employee)
        employee_form.barcode = 'Test@badge1'
        with self.assertRaises(ValidationError):
            employee_form.save()

        employee_form.barcode = 'Testàë@badge'
        with self.assertRaises(ValidationError):
            employee_form.save()

        employee_form.barcode = 'Testbadge2'
        employee_form.save()

        self.assertEqual(employee_form.barcode, 'Testbadge2')

    def test_search_hr_employee_no_access(self):
        new_user = new_test_user(self.env, 'employee')
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
        })
        domain = Domain([
            ('name', '=', 'Test Employee'),
            ('active', '=', True)
        ]).optimize(self.env['hr.employee'])
        with self.assertNoLogs('odoo.domains'):
            self.assertEqual(
                employee.ids,
                self.env['hr.employee'].with_user(new_user).search(domain).ids,
            )

    def test_is_flexible(self):
        employee = self.env['hr.employee'].create({
            'name': 'Employee',
            'tz': 'Asia/Tokyo',
        })
        self.assertTrue(employee.resource_calendar_id)
        self.assertFalse(employee.is_flexible)
        self.assertFalse(employee.is_fully_flexible)

        employee.resource_calendar_id = False
        employee.hours_per_week = 40
        employee.hours_per_day = 8
        self.assertTrue(employee.is_flexible)
        self.assertFalse(employee.is_fully_flexible)

        employee.hours_per_week = 0
        employee.hours_per_day = 0
        self.assertTrue(employee.is_flexible)
        self.assertTrue(employee.is_fully_flexible)

    def test_resource_calendar_sync_with_employee_one(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'test calendar',
        })
        self.assertTrue(self.employee.resource_id)
        self.assertTrue(self.employee.resource_calendar_id)
        self.assertEqual(self.employee.resource_calendar_id, self.employee.resource_id.calendar_id)
        self.assertNotEqual(self.employee.resource_calendar_id, calendar)
        self.assertTrue(self.employee.resource_calendar_id, self.employee.resource_id.calendar_id)
        old_calendar = self.employee.resource_calendar_id
        old_version = self.employee.version_id
        old_version.date_version = old_version.date_version - relativedelta(days=1)
        self.employee.resource_calendar_id = calendar
        self.assertEqual(self.employee.resource_id.calendar_id, calendar)
        version = self.employee.create_version({'resource_calendar_id': old_calendar.id, 'date_version': fields.Date.today()})
        self.assertEqual(self.employee.current_version_id, version)
        self.assertNotEqual(self.employee.current_version_id, old_version)
        self.assertEqual(self.employee.resource_calendar_id, old_calendar)
        self.assertEqual(self.employee.resource_id.calendar_id, old_calendar)

    def test_job_title(self):
        first_job = self.env['hr.job'].create({'name': "first job"})
        second_job = self.env['hr.job'].create({'name': "second job"})

        with Form(self.employee_without_image) as employee_form:
            # Assign first job to employee, job title should be job name
            employee_form.job_id = first_job
            self.assertEqual(employee_form.job_title, first_job.name)

            # Change job title, job name should not change
            employee_form.job_title = "custom job title"
            self.assertEqual(first_job.name, "first job")

            # Change the name of the first job, job title should not be updated
            first_job.name = "first job modified"
            self.assertEqual(employee_form.job_title, "custom job title")
            employee_form.save()

            # Assign second job to employee, job title should be second job name
            employee_form.job_id = second_job
            self.assertEqual(employee_form.job_title, second_job.name)

            # Switch back to first job, job title should be first job name
            employee_form.job_id = first_job
            self.assertEqual(employee_form.job_title, first_job.name)

    def test_user_creation_from_employee_with_invalid_email(self):
        # An unparseable work email no longer blocks creation: the employee still
        # gets a self-service user, with a synthetic (non-email) login.
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_email': 'not-an-email',
        })
        self.assertTrue(employee.user_id)
        self.assertTrue(employee.user_id.login.startswith('__emp_'))
        self.assertEqual(employee.user_id.role, 'group_user')

    def test_user_creation_from_employee_emails(self):
        # A new email creates a lite user with that login.
        new_emp = self.env['hr.employee'].create({
            'name': 'New Employee', 'work_email': 'newuser@example.com'})
        self.assertEqual(new_emp.user_id.login, 'newuser@example.com')
        self.assertFalse(new_emp.user_id.share)

        # An email matching an existing user that has no employee links to it
        # (by login or email address) rather than creating a duplicate.
        free_user = self.env['res.users'].create({
            'name': 'Free', 'login': 'free_login', 'email': 'free@example.com'})
        linked_emp = self.env['hr.employee'].create({
            'name': 'Linked', 'work_email': 'free@example.com'})
        self.assertEqual(linked_emp.user_id, free_user)

        # An email matching a user that already backs an employee does not reuse
        # it: a separate user is provisioned for the new employee.
        other_emp = self.env['hr.employee'].create({
            'name': 'Other', 'work_email': 'free@example.com'})
        self.assertTrue(other_emp.user_id)
        self.assertNotEqual(other_emp.user_id, free_user)

        # A multi/RFC-formatted email uses the first address as the login.
        multi_emp = self.env['hr.employee'].create({
            'name': 'Multi', 'work_email': '"N1" <n1@example.com>, "N2" <n2@example.com>'})
        self.assertEqual(multi_emp.user_id.login, 'n1@example.com')

        # No email at all still yields a user with a synthetic login (no crash).
        no_email_emp = self.env['hr.employee'].create({'name': 'No Email'})
        self.assertTrue(no_email_emp.user_id.login.startswith('__emp_'))

    def test_user_contact_phone_sync(self):
        partner = self.env['res.partner'].create({'name': 'Partner Test'})
        first_company = self.env['res.company'].create({'name': 'First Company'})
        first_employee = self.env['hr.employee'].create({
            'name': 'First Employee',
            'work_contact_id': partner.id,
            'company_id': first_company.id,
        })
        first_employee.write({'work_phone': '12345', 'work_email': 'first_employee@test.com'})
        self.assertEqual(first_employee.work_phone, partner.phone)
        self.assertEqual(first_employee.work_email, partner.email)
        partner.write({'phone': '67890', 'email': 'partner@test.com'})
        self.assertEqual(partner.phone, first_employee.work_phone)
        self.assertEqual(partner.email, first_employee.work_email)

        second_company = self.env['res.company'].create({'name': 'Second Company'})
        second_employee = self.env['hr.employee'].create({
            'name': 'Second Employee',
            'work_contact_id': partner.id,
            'company_id': second_company.id,
        })
        second_employee.write({'work_phone': '112233', 'work_email': 'second_employee@test.com'})
        self.assertNotEqual(second_employee.work_phone, partner.phone)
        self.assertNotEqual(second_employee.work_phone, first_employee.work_phone)
        self.assertNotEqual(second_employee.work_email, partner.email)
        self.assertNotEqual(second_employee.work_email, first_employee.work_email)
        partner.write({'phone': '445566', 'email': 'partner_updated@test.com'})
        self.assertNotEqual(partner.phone, second_employee.work_phone)
        self.assertNotEqual(partner.phone, first_employee.work_phone)
        self.assertNotEqual(partner.email, second_employee.work_email)
        self.assertNotEqual(partner.email, first_employee.work_email)

    def test_work_phone_companion_fields_are_invalidated(self):
        country = self.env.ref('base.be')
        company = self.env['res.company'].create({
            'name': 'Belgian Company',
            'country_id': country.id,
        })
        employee = self.env['hr.employee'].create({
            'name': 'Phone Employee',
            'company_id': company.id,
        })

        first_phone = '0456998877'
        employee.work_phone = first_phone
        first_sanitized = phone_validation.phone_format(
            first_phone, country.code, country.phone_code, force_format='E164'
        )
        self.assertEqual(employee.work_phone_sanitized, first_sanitized)
        self.assertEqual(
            employee.work_phone_formatted,
            phone_validation.phone_format(
                first_sanitized, country.code, country.phone_code, force_format='INTERNATIONAL'
            ),
        )

        second_phone = '0456112233'
        employee.work_phone = second_phone
        second_sanitized = phone_validation.phone_format(
            second_phone, country.code, country.phone_code, force_format='E164'
        )
        self.assertEqual(employee.work_phone_sanitized, second_sanitized)
        self.assertEqual(
            employee.work_phone_formatted,
            phone_validation.phone_format(
                second_sanitized, country.code, country.phone_code, force_format='INTERNATIONAL'
            ),
        )

    def test_restricted_phone_companion_fields(self):
        """emergency_phone / private_phone expose sanitized + formatted
        companions and keep their raw value (formatting is display-only)."""
        country = self.env.ref('base.be')
        company = self.env['res.company'].create({
            'name': 'Belgian Company',
            'country_id': country.id,
        })
        employee = self.env['hr.employee'].create({
            'name': 'Phone Employee',
            'company_id': company.id,
        })

        for fname in ('emergency_phone', 'private_phone'):
            raw = '0456998877'
            employee[fname] = raw
            sanitized = phone_validation.phone_format(
                raw, country.code, country.phone_code, force_format='E164'
            )
            # raw value is preserved; only the companions hold the formatted forms
            self.assertEqual(employee[fname], raw)
            self.assertEqual(employee[f'{fname}_sanitized'], sanitized)
            self.assertEqual(
                employee[f'{fname}_formatted'],
                phone_validation.phone_format(
                    sanitized, country.code, country.phone_code, force_format='INTERNATIONAL'
                ),
            )

            # changing the number re-computes the companions
            new_raw = '0456112233'
            employee[fname] = new_raw
            new_sanitized = phone_validation.phone_format(
                new_raw, country.code, country.phone_code, force_format='E164'
            )
            self.assertEqual(employee[f'{fname}_sanitized'], new_sanitized)

    def test_restricted_phone_not_reformatted_in_form(self):
        """Editing emergency/private phone in a form must keep the raw value:
        the INTERNATIONAL-formatting onchange has been removed."""
        country = self.env.ref('base.be')
        company = self.env['res.company'].create({
            'name': 'Belgian Company',
            'country_id': country.id,
        })
        employee = self.env['hr.employee'].create({
            'name': 'Phone Employee',
            'company_id': company.id,
        })
        with Form(employee) as form:
            form.emergency_phone = '0456998877'
            form.private_phone = '0456112233'
        self.assertEqual(employee.emergency_phone, '0456998877')
        self.assertEqual(employee.private_phone, '0456112233')

    @freeze_time('2025-12-01 09-00-00')
    def test_presence_state_groupby(self):
        present_user_a, present_user_b, absent_user = self.env['res.users'].create([
            {
                'name': 'Present User A',
                'login': 'present_user_a',
                'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
                'notification_type': 'email',
            },
            {
                'name': 'Present User B',
                'login': 'present_user_b',
                'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
                'notification_type': 'email',
            },
            {
                'name': 'Absent User',
                'login': 'absent_user_a',
                'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
                'notification_type': 'email',
            },
        ])
        present_user_a.action_create_employee()
        present_user_b.action_create_employee()
        absent_user.action_create_employee()

        present_absent_emps = present_user_a.employee_ids | present_user_b.employee_ids | absent_user.employee_ids
        present_absent_emps.write({
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1)
        })

        out_working_emp = self.env['hr.employee'].create(
            {'name': 'Out of Office Employee', 'contract_date_start': False, 'contract_date_end': False}
        )

        self.env["mail.presence"]._update_presence(present_user_a)
        self.env["mail.presence"]._update_presence(present_user_b)

        employee_per_presence_state = self.env['hr.employee'].with_context(active_test=False)._read_group(
            domain=[('id', 'in', (present_user_a.employee_ids + present_user_b.employee_ids + absent_user.employee_ids + out_working_emp).ids)],
            groupby=['hr_presence_state'],
            aggregates=['id:recordset'],
        )
        self.assertEqual(len(employee_per_presence_state), 3)
        for presence_state, employees in employee_per_presence_state:
            if presence_state == 'present':
                self.assertEqual(employees.ids, [present_user_a.employee_ids.id, present_user_b.employee_ids.id])
            if presence_state == 'absent':
                self.assertEqual(employees.ids, [absent_user.employee_ids.id])
            if presence_state == 'out_of_working_hour':
                self.assertEqual(employees.ids, [out_working_emp.id])

    def test_employee_can_edit_proxy_fields_on_own_user(self):
        user = new_test_user(
            self.env,
            login='emp_test',
            groups='base.group_user',
        )
        employee = self.env['hr.employee'].create({
            'name': 'Employee Test',
            'user_id': user.id,
        })

        user_env = user.with_user(user)

        vals = {
            'legal_name': 'Legal Name Self',
            'children': 2,
            'birthday': date(1990, 1, 1),
            'birthday_public_display': True,
            'place_of_birth': 'Brussels',
            'country_of_birth': self.env.ref('base.be').id,
            'marital': 'married',
            'spouse_complete_name': 'Alex Test',
            'spouse_birthdate': date(1991, 2, 3),
            'sex': 'male',
        }
        user_env.write(vals)

        self.assertEqual(user_env.legal_name, vals['legal_name'])
        self.assertEqual(user_env.children, vals['children'])
        self.assertEqual(user_env.birthday, vals['birthday'])
        self.assertEqual(user_env.birthday_public_display, vals['birthday_public_display'])
        self.assertEqual(user_env.place_of_birth, vals['place_of_birth'])
        self.assertEqual(user_env.country_of_birth.id, vals['country_of_birth'])
        self.assertEqual(user_env.marital, vals['marital'])
        self.assertEqual(user_env.spouse_complete_name, vals['spouse_complete_name'])
        self.assertEqual(user_env.spouse_birthdate, vals['spouse_birthdate'])
        self.assertEqual(user_env.sex, vals['sex'])

        self.assertEqual(employee.legal_name, vals['legal_name'])
        self.assertEqual(employee.children, vals['children'])
        self.assertEqual(employee.birthday, vals['birthday'])
        self.assertEqual(employee.birthday_public_display, vals['birthday_public_display'])
        self.assertEqual(employee.place_of_birth, vals['place_of_birth'])
        self.assertEqual(employee.country_of_birth.id, vals['country_of_birth'])
        self.assertEqual(employee.marital, vals['marital'])
        self.assertEqual(employee.spouse_complete_name, vals['spouse_complete_name'])
        self.assertEqual(employee.spouse_birthdate, vals['spouse_birthdate'])
        self.assertEqual(employee.sex, vals['sex'])

    def test_employee_cannot_edit_others_proxy_fields(self):
        user1 = new_test_user(self.env, login='emp_u1', groups='base.group_user')
        user2 = new_test_user(self.env, login='emp_u2', groups='base.group_user')

        emp1 = self.env['hr.employee'].create({'name': 'Emp 1', 'user_id': user1.id})
        self.env['hr.employee'].create({'name': 'Emp 2', 'user_id': user2.id})

        with self.assertRaises(AccessError):
            user1.with_user(user2).write({
                'legal_name': 'Hacked',
                'children': 99,
            })

        self.assertNotEqual(emp1.sudo().legal_name, 'Hacked')
        self.assertNotEqual(emp1.sudo().children, 99)


@tagged('-at_install', 'post_install')
class TestHrEmployeeLinks(HttpCase):
    def test_shared_private_link_permissions(self):
        """
        Employees not part of group_hr_user are not supposed to be able to see
        private employees pages (e.g.: from a shared link).
        The tour will check if the correct redirection warning appears when such
        case happens.
        """
        user_amy = new_test_user(
            self.env,
            name="Amy Rose",
            login='amy',
            groups='base.group_user'  # cannot access private employee profiles
        )
        employee_sonic = self.env['hr.employee'].create({
            'name': 'Sonic the Hedgehog',
        })
        with mute_logger('odoo.http'):  # ignore raised RedirectWarning
            self.start_tour(
                f"/odoo/employees/{employee_sonic.id}",
                "check_public_employee_link_redirect",
                login=user_amy.login,
            )


@tagged('-at_install', 'post_install')
class TestVersionCron(TransactionCase):
    """Test the behavior of CRONs affecting hr.version"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Will be used for default employee version address (contains phone)
        cls.env.user.company_id = cls.env['res.company'].create(
            {'name': 'Pokémon Center', 'phone': '+32404040404'}
        )

        # Employee has a default version that will be overridden
        with freeze_time("2020-10-07"):
            cls.employee = cls.env['hr.employee'].create(
                {
                    'name': 'Charizard',
                    'work_phone': '+32404040404',
                    "distance_home_work": 32,
                    "distance_home_work_unit": 'miles',
                }
            )

    def test_version_cron_update_no_fields(self):
        """
        Employees should not see their fields be updated if the CRON does not
        change their version.
        """
        with freeze_time('2023-10-06'):
            self.employee.create_version(
                {'date_version': '2023-10-07', "distance_home_work": 40}
            )

        # Saving current employee data to compare later on
        employee_values = {}
        # some fields cannot be accessed. We need to filter them out
        employee_fields = [
            field
            for field in self.env['hr.employee']._fields
            if hasattr(self.employee, field)
        ]
        for field in employee_fields:
            employee_values[field] = self.employee[field]

        # Should not change to new version
        with freeze_time('2023-10-06'):
            self.env['hr.employee']._cron_update_current_version_id()

        for field in employee_fields:
            self.assertEqual(
                employee_values[field],
                self.employee[field],
                f"""No field should change if _cron_update_current_version_id() does not change the version.
    However, the field {field} changed""",
            )

    def test_version_cron_update_fields(self):
        """
        Employees should see some of their field be changed if the CRON changes
        their version.
        """
        with freeze_time('2023-10-06'):
            self.employee.create_version(
                {'date_version': '2023-10-07', "distance_home_work": 40}
            )
        current_home_distance = self.employee.distance_home_work
        current_version = self.employee.current_version_id
        # Should change to new version
        with freeze_time('2023-10-07'):
            self.env['hr.employee']._cron_update_current_version_id()

        self.assertNotEqual(
            current_version,
            self.employee.current_version_id,
            "current_version_id should have changed after calling _cron_update_current_version_id()",
        )
        self.assertNotEqual(
            current_home_distance,
            self.employee.distance_home_work,
            "distance_home_work should have changed after calling _cron_update_current_version_id()",
        )


@tagged('-at_install', 'post_install')
class TestHrEmployeeWebJson(HttpCase):

    def setUp(self):
        super().setUp()
        # JSON route needs to be enabled for the tests
        self.env['ir.config_parameter'].sudo().set_bool('web.json.enabled', True)

    def test_webjson_employees(self):
        # Check that json employees can be accessed
        url = "/json/1/employees"
        self.env['ir.config_parameter'].set_bool('web.json.enabled', True)
        self.authenticate('admin', 'admin')
        CSRF_USER_HEADERS = {
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": 'none',
            "Sec-Fetch-User": "?1",
        }
        res = self.url_open(url, headers=CSRF_USER_HEADERS)
        self.assertEqual(res.status_code, 200)
