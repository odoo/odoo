# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestProjectStock(TestProjectCommon):
    def test_check_company(self):
        """
            tests editing relation fields of a partner from a project
        """
        self.project_pigs.partner_id = self.env['res.partner'].create({
            'name': 'Jeff Delaney',
        })
        self.env['stock.warehouse'].create({
            'name': 'Hi mom!',
            'partner_id': self.project_pigs.partner_id.id,
            'code': 'Fireship',
        })
