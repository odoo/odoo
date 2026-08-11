# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged, new_test_user, users
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestPosHrHttpCommon(TestPointOfSaleHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.env.ref('hr.group_hr_user')
        cls.env.user.group_ids |= cls.env.ref('hr.group_hr_manager')
        payroll_user_group = cls.env.ref("hr_payroll.group_hr_payroll_user", raise_if_not_found=False)
        if payroll_user_group:
            cls.env.user.group_ids |= payroll_user_group

        # Admin employee
        cls.pos_admin.employee_id.name = "Mitchell Admin"
        cls.admin = cls.pos_admin.employee_id

        cls.main_pos_config.write({"module_pos_hr": True})

        # Managers
        cls.manager_user = new_test_user(
            cls.env,
            login="manager_user",
            groups="point_of_sale.group_pos_manager",
            name="Pos Manager",
            email="manager_user@pos.com",
        )
        cls.manager1 = cls.env['hr.employee'].create({
            'name': 'Test Manager 1',
            "company_id": cls.env.company.id,
            "user_id": cls.manager_user.id,
            "pin": "5651"
        })
        cls.manager2 = cls.env['hr.employee'].create({
            'name': 'Test Manager 2',
            "company_id": cls.env.company.id,
            "pin": "5652"
        })

        # User employee
        cls.emp1 = cls.env['hr.employee'].create({
            'name': 'Test Employee 1',
            "company_id": cls.env.company.id,
        })
        emp1_user = new_test_user(
            cls.env,
            login="emp1_user",
            groups="base.group_user, point_of_sale.group_pos_user, account.group_account_invoice",
            name="Pos Employee1",
            email="emp1_user@pos.com",
        )
        cls.emp1.write({"name": "Pos Employee1", "pin": "2580", "user_id": emp1_user.id})

        # Non-user employee
        cls.emp2 = cls.env['hr.employee'].create({
            'name': 'Test Employee 2',
            "company_id": cls.env.company.id,
        })
        cls.emp2.write({"name": "Pos Employee2", "pin": "1234"})
        (cls.admin + cls.emp1 + cls.emp2).company_id = cls.env.company

        cls.emp3 = cls.env['hr.employee'].create({
            'name': 'Test Employee 3',
            "user_id": cls.pos_user.id,
            "company_id": cls.env.company.id,
        })

        cls.emp4 = cls.env['hr.employee'].create({
            'name': 'Test Employee 4',
            "company_id": cls.env.company.id,
        })

        cls.main_pos_config.write({
            'basic_employee_ids': [Command.link(cls.emp1.id), Command.link(cls.emp2.id), Command.link(cls.emp3.id)],
            'minimal_employee_ids': [Command.link(cls.emp4.id)],
            'advanced_employee_ids': [Command.link(cls.manager1.id), Command.link(cls.manager2.id)]
        })


@tagged("post_install", "-at_install")
class TestUi(TestPosHrHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    def test_cashier_stay_logged_in(self):
        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.with_user(self.pos_admin).open_ui()

        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "CashierStayLogged",
            login="pos_admin",
        )

    def test_change_on_rights_reflected_directly(self):
        """When changes in employee rights (advanced/basic/minimal) should
        be reflected directly and not read from the cache."""

        self.main_pos_config.advanced_employee_ids = self.pos_admin.employee_id
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_change_on_rights_reflected_directly",
            login="pos_admin",
        )

    def test_cashier_changed_in_receipt_and_mail(self):
        """
        Checks that when the cashier is changed during the order,
        the receipts displays the employee that concluded the order,
        meaning the one that was at the register when the customer was paying.
        Also checks that the order has the right cashier and employee in the same
        use case.
        """
        self.product_a.available_in_pos = True
        self.main_pos_config.with_user(self.pos_admin).open_ui()

        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_cashier_changed_in_receipt",
            login="pos_admin",
        )
        order = self.main_pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.cashier, "Test Employee 3")
        self.assertEqual(order.employee_id.display_name, "Test Employee 3")
        mail_receipt_data = order.order_receipt_generate_data(False)
        self.assertEqual(mail_receipt_data['extra_data']['cashier_name'], "Test")

    @users('pos_admin')
    def test_create_pos_config_without_hr_right(self):
        self.env['pos.config'].create({
            'name': 'My cute pos config',
            'module_pos_hr': True,
            'advanced_employee_ids': [(6, 0, self.emp2.ids)]
        })

    def test_go_backend(self):
        self.main_pos_config.with_user(self.manager_user).open_ui()

        self.start_pos_tour("pos_hr_go_backend_closed_registered", login="manager_user")
        self.start_pos_tour("pos_hr_go_backend_opened_registered", login="manager_user")
        self.start_pos_tour("pos_hr_go_backend_opened_registered_different_user_logged", login="emp1_user")

    def test_maximum_closing_difference(self):
        self.main_pos_config.set_maximum_difference = True
        self.main_pos_config.amount_authorized_diff = 0

        # Admin users should still be able to override max difference
        # regardless if they are the connected user or not
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_maximum_closing_difference",
            login="pos_user"
        )

        # Advanced rights employees should not override max difference
        # when the connected user has admin rights (they never should)
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_maximum_closing_difference",
            login="pos_admin"
        )

    def test_logged_employee_ids_tracking(self):
        """Test that logged_employee_ids tracks all employees who logged into the session."""
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_logged_employee_ids_tracking",
            login="pos_user",
        )

        self.assertEqual(len(self.main_pos_config.logged_employee_ids), 3, "Session should have exactly 3 logged employees.")
        self.assertEqual(
            set(self.main_pos_config.current_session_id.logged_employee_ids.mapped('name')),
            {"Mitchell Admin", "Pos Employee1", "Pos Employee2"},
            "Logged employees don't match expected",
        )
