# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo import tools


@tagged('post_install')
class TestUi(HttpCase):

    def test_01_sale_project_mrp_tour(self):
        kit_product = self.env['product.template'].create({
                'name': 'super kit',
                'type': 'consu'
        })
        service_type = ['task_in_project', 'project_only', 'task_global_project']
        services = []
        for s_type in service_type:
            services.append(self.env['product.product'].create({
                'name': 'services : %s' % (s_type),
                'type': 'service',
                'service_tracking': s_type
            }))
        bom_lines = []
        for service in services:
            bom_lines.append((0, 0, {
                'product_id': service.id
            }))
        BOM = self.env['mrp.bom'].create({
            'type': 'phantom',
            'product_tmpl_id': kit_product.id,
            'bom_line_ids': bom_lines
        })
        self.start_tour("/web", 'sale_project_mrp_tour', login="admin")
        projects = []
        tasks = []
        # check that a project have been created for each bom_line with a service
        for bom_line in BOM.bom_line_ids:
            projects += self.env['project.project'].search([('bom_line_id', '=', bom_line.id)])
            tasks += self.env['project.task'].search([('bom_line_id', '=', bom_line.id)])
        # There should 2 project generated. One for project_only and One for task_in_project
        self.assertEqual(len(projects), 2, "One or more project wasn't generated properly for a kit")
        # There should be 2 tasks generated one for task_global_projects and one for task_in project
        self.assertEqual(len(tasks), 2, "One or more tasks wasn't generated properly for a kit")
