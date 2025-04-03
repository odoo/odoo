# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSaleProjectCommon
from odoo.tests.common import HttpCase
from odoo.tests import new_test_user, tagged


@tagged('post_install', '-at_install')
class TestUi(TestSaleProjectCommon, HttpCase):

    def test_sale_order_milestone_with_no_project_rights(self):
        milestone_user = new_test_user(
            self.env, groups='project.group_project_milestone,sales_team.group_sale_salesman',
            login='Milestone user', name='Milestone user',
        )

        group_project_user = self.env.ref('project.group_project_user').id
        self.assertTrue(group_project_user not in milestone_user.groups_id.ids)

        self.env['product.product'].create({
            'name': "Service Based on Milestones",
            'type': 'service',
            'service_policy': 'delivered_milestones',
            'service_type': 'milestones',
            'project_id': False,
        })

        self.start_tour(
            "/web#action=sale.action_quotations&model=sale.order&view_type=form",
            'project_milestone_sale_quote_tour',
            login="Milestone user",
        )

        sale_order = self.env['sale.order'].search([])
        self.assertTrue(sale_order, "A sale order should have been created.")
