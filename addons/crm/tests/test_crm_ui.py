# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.tests import HttpCase
from odoo.tests.common import tagged, users


@tagged('post_install', '-at_install')
class TestUi(HttpCase):

    def test_01_crm_tour(self):
        self.start_tour("/web", 'crm_tour', login="admin")

    def test_02_crm_tour_rainbowman(self):
        # we create a new user to make sure he gets the 'Congrats on your first deal!'
        # rainbowman message.
        self.env['res.users'].create({
            'name': 'Temporary CRM User',
            'login': 'temp_crm_user',
            'password': 'temp_crm_user',
            'groups_id': [(6, 0, [
                    self.ref('base.group_user'),
                    self.ref('sales_team.group_sale_salesman')
                ])]
        })
        self.start_tour("/web", 'crm_rainbowman', login="temp_crm_user")

    def test_03_crm_tour_forecast(self):
        self.start_tour("/web", 'crm_forecast', login="admin")

class TestCRMLeadMisc(TestCrmCommon):

    @users('user_sales_leads')
    def test_team_my_pipeline(self):
        action = self.env['crm.team'].action_your_pipeline()
