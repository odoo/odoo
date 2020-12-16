# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.api import Environment
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date, timedelta

from odoo.tests import Form, tagged, new_test_user
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestPosHrHttpCommon(TestPointOfSaleHttpCommon):
    def setUp(self):
        super().setUp()
        self.main_pos_config.write({"module_pos_hr": True})

        # Admin employee
        self.env.ref("hr.employee_admin").write(
            {"name": "Mitchell Admin", "pin": False}
        )

        # User employee
        emp1 = self.env.ref("hr.employee_han")
        emp1_user = new_test_user(
            self.env,
            login="emp1_user",
            groups="base.group_user",
            name="Pos Employee1",
            email="emp1_user@pos.com",
        )
        emp1.write({"name": "Pos Employee1", "pin": "2580", "user_id": emp1_user.id})

        # Non-user employee
        emp2 = self.env.ref("hr.employee_jve")
        emp2.write({"name": "Pos Employee2", "pin": "1234"})

        with Form(self.main_pos_config) as config:
            config.employee_ids.add(emp1)
            config.employee_ids.add(emp2)


@tagged("post_install", "-at_install")
class TestUi(TestPosHrHttpCommon):
    def test_01_pos_hr_tour(self):
        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.open_session_cb(check_coa=False)

        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "PosHrTour",
            login="admin",
        )
