# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.api import Environment
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date, timedelta

from odoo.tests import Form, tagged, new_test_user
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


class TestPosHrHttpCommon(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.user.groups_id += cls.env.ref('hr.group_hr_user')

        cls.main_pos_config.write({"module_pos_hr": True})

        # Admin employee
        admin = cls.env.ref("hr.employee_admin").sudo().copy({
            "company_id": cls.env.company.id,
            "user_id": cls.env.user.id,
            "name": "Mitchell Admin",
            "pin": False,
        })

        # User employee
        emp1 = cls.env.ref("hr.employee_han").sudo().copy({
            "company_id": cls.env.company.id,
        })
        emp1_user = new_test_user(
            cls.env,
            login="emp1_user",
            groups="base.group_user",
            name="Pos Employee1",
            email="emp1_user@pos.com",
        )
        emp1.write({"name": "Pos Employee1", "pin": "2580", "user_id": emp1_user.id})

        # Non-user employee
        emp2 = cls.env.ref("hr.employee_jve").sudo().copy({
            "company_id": cls.env.company.id,
        })
        emp2.write({"name": "Pos Employee2", "pin": "1234"})
        (admin + emp1 + emp2).company_id = cls.env.company

        with Form(cls.main_pos_config) as config:
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
            login="accountman",
        )
