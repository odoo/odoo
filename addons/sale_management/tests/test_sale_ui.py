<<<<<<< HEAD
# -*- coding: utf-8 -*-
||||||| parent of 598015810be9 (temp)
import odoo.tests
=======
>>>>>>> 598015810be9 (temp)
# Part of Odoo. See LICENSE file for full copyright and licensing details.

<<<<<<< HEAD
from odoo.tests import HttpCase, tagged
||||||| parent of 598015810be9 (temp)
=======
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged, HttpCase
>>>>>>> 598015810be9 (temp)

<<<<<<< HEAD

@tagged('post_install', '-at_install')
class TestUi(HttpCase):
||||||| parent of 598015810be9 (temp)
@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
=======

@tagged('post_install', '-at_install')
class TestUi(AccountTestInvoicingCommon, HttpCase):
>>>>>>> 598015810be9 (temp)

    def test_01_sale_tour(self):
        self.start_tour("/web", 'sale_tour', login="admin", step_delay=100)

    def test_02_sale_tour_company_onboarding_done(self):
        self.env.company.set_onboarding_step_done('base_onboarding_company_state')
        self.start_tour("/web", 'sale_tour', login="admin", step_delay=100)

    def test_03_sale_quote_tour(self):
        self.env['res.partner'].create({'name': 'Agrolait', 'email': 'agro@lait.be'})
        self.start_tour("/web", 'sale_quote_tour', login="admin", step_delay=100)
