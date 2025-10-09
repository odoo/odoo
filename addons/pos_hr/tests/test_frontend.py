# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged, new_test_user, users
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestPosHrHttpCommon(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.env.ref('hr.group_hr_user')

        cls.main_pos_config.write({"module_pos_hr": True})

        # Admin employee
        cls.admin = cls.env.ref("hr.employee_admin").sudo().copy({
            "date_version": '2000-01-01',
            "company_id": cls.env.company.id,
            "user_id": cls.pos_admin.id,
            "name": "Mitchell Admin",
            "pin": False,
        })

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
            groups="base.group_user",
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
    def test_01_pos_hr_tour(self):
        self.pos_admin.write({
            "group_ids": [
                (4, self.env.ref('account.group_account_invoice').id)
            ]
        })
        self.main_pos_config.update({
            'advanced_employee_ids': [(6, 0, self.admin.ids)],
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour("PosHrTour", login="pos_admin")

    def test_cashier_stay_logged_in(self):
        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.with_user(self.pos_admin).open_ui()

        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "CashierStayLogged",
            login="pos_admin",
        )

    def test_cashier_can_see_product_info(self):
        # open a session, the /pos/ui controller will redirect to it
        self.product_a.available_in_pos = True
        self.main_pos_config.with_user(self.pos_admin).open_ui()

        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "CashierCanSeeProductInfo",
            login="pos_admin",
        )

    def test_basic_user_cannot_close_session(self):
        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.advanced_employee_ids = []
        self.main_pos_config.basic_employee_ids = [
            Command.link(self.emp3.id),
        ]
        self.main_pos_config.with_user(self.pos_admin).open_ui()

        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "CashierCannotClose",
            login="pos_user",
        )

    def test_basic_user_can_change_price(self):
        self.main_pos_config.advanced_employee_ids = []
        self.main_pos_config.basic_employee_ids = [
            Command.link(self.emp3.id),
            Command.link(self.admin.id)
        ]
        self.main_pos_config.write({
            "restrict_price_control": False,
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()

        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_basic_user_can_change_price",
            login="pos_user",
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

    def test_cashier_changed_in_receipt(self):
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

    def test_minimal_employee_refund(self):
        minimal_emp = self.env['hr.employee'].create({
            'name': 'Minimal Employee',
            "company_id": self.env.company.id,
        })
        self.main_pos_config.update({
            'minimal_employee_ids': [(6, 0, minimal_emp.ids)],
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        current_session = self.main_pos_config.current_session_id
        current_session.set_opening_control(0, None)
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_a.id,
            'pricelist_id': self.partner_a.property_product_pricelist.id,
            'lines': [
                Command.create({
                    'product_id': self.product_a.id,
                    'qty': 1,
                    'price_subtotal': 100.0,
                    'price_subtotal_incl': 100.0,
                }),
            ],
            'amount_tax': 0.0,
            'amount_total': 100.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 100,
            'payment_method_id': self.bank_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        self.start_pos_tour("test_minimal_employee_refund", login="pos_admin")

    def test_cost_and_margin_visibility(self):
        self.product_a.available_in_pos = True
        self.main_pos_config.write({
            'is_margins_costs_accessible_to_every_user': True,
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()

        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_cost_and_margin_visibility",
            login="pos_admin",
        )

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
