# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.pos_hr.tests.test_common import TestPosHrDataHttpCommon


@tagged("post_install", "-at_install")
class TestUi(TestPosHrDataHttpCommon):
    def test_01_pos_hr_tour(self):
        self.pos_admin.group_ids |= self.env.ref("account.group_account_invoice")
        self.start_pos_tour("PosHrTour", login="pos_admin")

    def test_cashier_stay_logged_in(self):
        self.start_pos_tour("CashierStayLogged", login="pos_admin")

    def test_cashier_can_see_product_info(self):
        self.start_pos_tour("CashierCanSeeProductInfo", login="pos_admin")

    def test_basic_user_cannot_close_session(self):
        self.start_pos_tour("CashierCannotClose")
