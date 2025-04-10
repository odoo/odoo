# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from dateutil.relativedelta import relativedelta
from psycopg2.errors import UniqueViolation

from odoo import fields
from odoo.fields import Domain
from odoo.tests import Form, users, new_test_user, HttpCase, tagged
from odoo.addons.hr.tests.common import TestHrCommon
from odoo.tools import mute_logger
from odoo.exceptions import ValidationError

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

        partner.with_company(company_A)._compute_employees_count()
        self.assertEqual(partner.employees_count, 1)
        partner.with_company(company_B)._compute_employees_count()
        self.assertEqual(partner.employees_count, 1)
        single_company_action = partner.with_company(company_B).action_open_employees()
        self.assertEqual(single_company_action.get('view_mode'), 'form')
        partner.with_company(company_A).with_company(company_B)._compute_employees_count()
        self.assertEqual(partner.employees_count, 2)
        multi_company_action = partner.with_company(company_A).with_company(company_B).action_open_employees()
        self.assertEqual(multi_company_action.get('view_mode'), 'kanban')

    def test_employee_linked_partner(self):
        user_partner = self.user_without_image.partner_id
        work_contact = self.employee_without_image.work_contact_id
        self.assertEqual(user_partner, work_contact)

    def test_employee_resource(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee = employee_form.save()
        self.assertEqual(employee.tz, _tz)

    def test_employee_from_user(self):
        _tz = 'Pacific/Apia'
        _tz2 = 'America/Tijuana'
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
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
        self.assertEqual(self.employee_without_image.avatar_1920, self.user_without_image.avatar_1920)

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
        self.res_users_hr_officer.employee_id = emp
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

    def test_employee_update_work_contact_id(self):
        """
            Check that the `work_contact_id` information is no longer
            updated when an employee's `user_id` is added to another employee.
        """
        user = self.env['res.users'].create({
            'name': 'Test',
            'login': 'test',
            'email': 'test@example.com',
        })
        employee_A, employee_B = self.env['hr.employee'].create([
            {
                'name': 'Employee A',
                'user_id': user.id,
                'work_email': 'employee_A@example.com',
            },
            {
                'name': 'Employee B',
                'user_id': False,
                'work_email': 'employee_B@example.com',
            }
        ])
        employee_A.user_id = False
        employee_B.user_id = user.id
        employee_B.work_email = 'new_email@example.com'
        self.assertEqual(employee_A.work_email, 'employee_A@example.com')
        self.assertEqual(employee_B.work_email, 'new_email@example.com')
        self.assertFalse(employee_A.work_contact_id)
        self.assertEqual(employee_B.work_contact_id, user.partner_id)

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
        user_fields = ['email', 'phone', 'im_status']
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
            'acc_number' : '1234567',
            'partner_id' : test_user.partner_id.id,
        })
        test_employee = self.env['hr.employee'].create({
            'name': 'Test User - employee',
            'user_id': test_user.id,
            'company_id': test_company.id,
            'bank_account_id': bank_account.id,
        })
        # change user -> bank account change company
        with Form(test_employee) as employee_form:
            employee_form.user_id = test_other_user
        # change user back -> check that there is no company error
        with Form(test_employee) as employee_form:
            employee_form.user_id = test_user

    def test_change_user_on_employee_keep_partner(self):
        """
            Check that removing user from employee keeps the link in
            work_contact_id until the user is assigned to another employee.
        """
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
        })
        employee = self.env['hr.employee'].create({
            'name': 'Test User - employee',
            'user_id': user.id,
        })
        # remove user
        employee.user_id = None
        self.assertEqual(employee.work_contact_id, user.partner_id)
        self.assertFalse(employee.user_id)
        # create new employee from user
        user._compute_company_employee()
        user.action_create_employee()
        self.assertTrue(len(user.employee_ids) == 1, "Test user should have exactly one employee associated with it")
        # previous employee shouldn't have a work_contact_id anymore, as the partner is reassigned
        self.assertFalse(employee.work_contact_id)
        # the new employee should be associated to both the user and its partner
        new_employee = user.employee_ids
        self.assertEqual(new_employee.work_contact_id, user.partner_id)
        self.assertEqual(new_employee.user_id, user)

    def test_change_user_on_employee_multi_company(self):
        """
            Removing user from employee keeps the link in work_contact_id in the correct company until the user
            is assigned to another employee, and does not affect employees in other companies. When the unique
            constraint of one employee per user in one company is triggered, the work_contact_id for the
            existing employee is nor removed, and employees in other companies are not affected.
        """
        company_A = self.env['res.company'].create({'name': 'company_A'})
        company_B = self.env['res.company'].create({'name': 'company_B'})
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
        })
        partner = user.partner_id
        employee_A = self.env['hr.employee'].create({
            'name': 'employee_A',
            'user_id': user.id,
            'company_id': company_A.id,
        })
        employee_B = self.env['hr.employee'].create({
            'name': 'employee_B',
            'user_id': user.id,
            'company_id': company_B.id
        })
        # Creating an employee in one company does not remove the link with employee in the other company
        self.assertEqual(user.with_company(company_A).employee_id, employee_A)
        self.assertEqual(user.with_company(company_B).employee_id, employee_B)
        # Partner is linked to both employees
        partner.with_company(company_A).with_company(company_B)._compute_employees_count()
        self.assertEqual(partner.employees_count, 2)
        # Remove user from employee in one company does not affect link user-employee in the other company
        employee_A.user_id = None
        self.assertEqual(user.with_company(company_A).employee_id.ids, [])
        self.assertEqual(user.with_company(company_B).employee_id, employee_B)
        # Partner still linked to both employees
        partner.with_company(company_A).with_company(company_B)._compute_employees_count()
        self.assertEqual(partner.employees_count, 2)
        # Creating a new employee for a user in company A does not affect link user-employee in the other company
        new_employee_A = self.env['hr.employee'].create({
            'name': 'new_employee_A',
            'user_id': user.id,
            'company_id': company_A.id,
        })
        # User cannot be assigned to more than one employee in the same company. work_contact_id should not be removed.
        with mute_logger('odoo.sql_db'), self.assertRaises(UniqueViolation), self.assertRaises(ValidationError):
            self.env['hr.employee'].create({
                'name': 'new_employee_B',
                'user_id': user.id,
                'company_id': company_B.id,
            })
        self.assertEqual(user.with_company(company_A).employee_id, new_employee_A)
        self.assertEqual(user.with_company(company_B).employee_id, employee_B)
        self.assertEqual(partner.employee_ids, employee_B + new_employee_A)

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
        self.assertEqual(employee_norbert.image_1920, user_norbert.image_1920)
        self.assertEqual(employee_norbert.avatar_1920, user_norbert.avatar_1920)

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

    def test_departure_wizard(self):
        """ Test the archiving wizard in the case of multiple employees """
        employee_A, employee_B, employee_C = self.env['hr.employee'].create([
            {
                'name': f'Employee {code}',
                'user_id': False,
                'work_email': f'employee_{code}@example.com',
            } for code in ['A', 'B', 'C']
        ])
        archiving_employees = [employee.id for employee in (employee_A, employee_C)]

        wizard = self.env['hr.departure.wizard'].with_context(
            employee_termination=True,
            active_ids=archiving_employees,
        ).create({})
        wizard.action_register_departure()

        all_employees = employee_A | employee_B | employee_C
        self.assertEqual(all_employees.filtered(lambda e: e.active), employee_B, "Employees should have been archived")

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
        })
        self.assertTrue(employee.resource_calendar_id)
        self.assertFalse(employee.is_flexible)
        self.assertFalse(employee.is_fully_flexible)

        employee.resource_calendar_id.flexible_hours = True
        self.assertTrue(employee.is_flexible)
        self.assertFalse(employee.is_fully_flexible)

        employee.resource_calendar_id = False
        self.assertTrue(employee.is_flexible)
        self.assertTrue(employee.is_fully_flexible)

    def test_resource_calendar_sync_with_employee_one(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'test calendar',
            'flexible_hours': True,
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

    def test_flexible_working_hours(self):
        """
        Test to verifie that get_unusual_days() return false for flexible work schedule
        """

        # Creating a flexible working schedule
        calendar_flex = self.env['resource.calendar'].create([
            {
                'tz': "Europe/Brussels",
                'name': 'flexible hours',
                'flexible_hours': "True",
            },
        ])
        employeeA = self.env['hr.employee'].create({
            'name': 'Employee',
        })

        # Testing employeA on regular working schedule
        days = employeeA._get_unusual_days(str(datetime(2025, 1, 1)), str(datetime(2025, 12, 31)))
        self.assertTrue(days)
        self.assertTrue(days['2025-01-04'])

        # Assigning flexible work hours to employeeA
        employeeA.resource_calendar_id = calendar_flex.id
        days = employeeA._get_unusual_days(str(datetime(2025, 1, 1)), str(datetime(2025, 12, 31)))
        self.assertTrue(days)
        self.assertFalse(days['2025-01-04'])

    def test_user_creation_from_employee_with_invalid_email(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_email': 'test'
        })

        action = employee.action_create_users()
        self.assertEqual(action['params']['message'], f'You need to set a valid work email address for {employee.name}')
        self.assertFalse(employee.user_id)

    def test_user_creation_from_employee_multi_emails(self):
        employees = self.env['hr.employee'].create([
            {
                'name': 'Existing Email Employee',
                'work_email': self.user_without_image.email,
            }, {
                'name': 'New Employee',
                'work_email': 'newuser@example.com',
            }, {
                'name': 'Invalid Email Employee',
                'work_email': 'invalid-email',
            }, {
                'name': 'Without Email Employee',
                'work_email': False,
            }, {
                'name': 'Formatted Email Employee',
                'work_email': f'"John Doe" <{self.user_without_image.email_normalized}>',
            }, {
                'name': 'Multi Email Employee',
                'work_email': '"Name1" <name@test.example.com>, "Name 2" <name2@test.example.com>',
            },
        ])
        # Add an existing employee who already has a user to the employee list
        employees += self.employee_without_image
        context = {'selected_ids': employees.ids}
        confirmed_employees = self.env['hr.employee'].with_context(context).browse(employees.ids)
        action = confirmed_employees.action_create_users()

        params = action.get('params')
        self.assertEqual(params.get('message'), f"User already exists with the same email for Employees {employees[0].name}, {employees[4].name}")
        params = params.get('next').get('params')
        self.assertEqual(params.get('message'), f"You need to set a valid work email address for {employees[2].name}, {employees[5].name}")
        params = params.get('next').get('params')
        self.assertEqual(params.get('message'), f"You need to set the work email address for {employees[3].name}")
        params = params.get('next').get('params')
        self.assertEqual(params.get('message'), f"User already exists for Those Employees {employees[6].name}")
        params = params.get('next').get('params')
        self.assertEqual(params.get('message'), f"Users {employees[1].name} creation successful")
        self.assertTrue(employees[1].user_id)


@tagged('-at_install', 'post_install')
class TestHrEmployeeWebJson(HttpCase):

    def setUp(self):
        super().setUp()
        # JSON route needs to be enabled for the tests
        self.env['ir.config_parameter'].sudo().set_param('web.json.enabled', True)

    def test_webjson_employees(self):
        # Check that json employees can be accessed
        url = "/json/1/employees"
        self.env['ir.config_parameter'].set_param('web.json.enabled', True)
        self.authenticate('admin', 'admin')
        CSRF_USER_HEADERS = {
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": 'none',
            "Sec-Fetch-User": "?1",
        }
        res = self.url_open(url, headers=CSRF_USER_HEADERS)
        self.assertEqual(res.status_code, 200)
