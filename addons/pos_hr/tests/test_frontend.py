# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged, new_test_user
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestPosHrHttpCommon(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.groups_id += cls.env.ref('hr.group_hr_user')

        cls.main_pos_config.write({"module_pos_hr": True})

        # Admin employee
        cls.admin = cls.env.ref("hr.employee_admin").sudo().copy({
            "company_id": cls.env.company.id,
            "user_id": cls.pos_admin.id,
            "name": "Mitchell Admin",
            "pin": False,
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

        cls.main_pos_config.write({
            'basic_employee_ids': [Command.link(cls.emp1.id), Command.link(cls.emp2.id)]
        })


@tagged("post_install", "-at_install")
class TestUi(TestPosHrHttpCommon):
    def test_01_pos_hr_tour(self):
        self.pos_admin.write({
            "groups_id": [
                (4, self.env.ref('account.group_account_invoice').id)
            ]
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour("PosHrTour", login="pos_admin")
        orders = self.env['pos.order'].search([])
        orders[0].employee_id = self.emp2
        orders[1].employee_id = self.emp1
        orders[2].employee_id = self.admin

    def test_cashier_stay_logged_in(self):
        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.with_user(self.pos_admin).open_ui()

        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "CashierStayLogged",
            login="pos_admin",
        )
