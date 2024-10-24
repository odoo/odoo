# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_timesheet.tests.test_sale_timesheet import TestSaleTimesheet
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPerformanceTimesheet(TestSaleTimesheet):

    def test_compute_sale_line(self):
        project = self.env['project.project'].create({
            'name': 'Billable Project',
            'allow_billable': True,
            'partner_id': self.partner_b.id,
        })
        tasks = self.env['project.task'].create([{
            'name': 'Task %s (%s)' % (i, project.name),
            'project_id': project.id,
        } for i in range(50)])
        tasks.sale_line_id = False
        self.env.invalidate_all()
        self.env.registry.clear_cache()
        with self.assertQueryCount(528):
            tasks._compute_sale_line()

        tasks = tasks | self.env['project.task'].create([{
            'name': 'Task %s (%s)' % (i, project.name),
            'project_id': project.id,
        } for i in range(50, 100)])
        tasks.sale_line_id = False
        self.env.invalidate_all()
        self.env.registry.clear_cache()
        with self.assertQueryCount(1029):
            tasks._compute_sale_line()
