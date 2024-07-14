# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.mrp.tests.common import TestMrpCommon

class TestBoMHr(TestMrpCommon):
    def test_bom_report_operation_cost(self):
        """ Test report bom overview with variant-exclusive operations, see if the bom cost matches.
        """
        self.workcenter_2.employee_costs_hour = 120
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_template_sofa.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': self.product_5.id, 'product_qty': 1}),
            ],
            'operation_ids': [
                Command.create({
                    'name': 'Operation Red',
                    'workcenter_id': self.workcenter_2.id,
                    'time_cycle_manual': 10,
                    'sequence': 1,
                    'bom_product_template_attribute_value_ids': [Command.link(self.product_7_attr1_v1.id)],
                }),
                Command.create({
                    'name': 'Operation Blue',
                    'workcenter_id': self.workcenter_2.id,
                    'time_cycle_manual': 20,
                    'sequence': 2,
                    'bom_product_template_attribute_value_ids': [Command.link(self.product_7_attr1_v2.id)],
                }),
                Command.create({
                    'name': 'Common opetation',
                    'workcenter_id': self.workcenter_2.id,
                    'time_cycle_manual': 60,
                    'sequence': 3,
                }),
            ],
        })

        report_red = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id, searchVariant=self.product_7_1.id)
        self.assertEqual(len(report_red['lines']['operations']), 2)
        self.assertEqual(report_red['lines']['operations'][0]['bom_cost'], 20)
        self.assertEqual(report_red['lines']['operations'][1]['bom_cost'], 120)

        report_blue = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id, searchVariant=self.product_7_2.id)
        self.assertEqual(len(report_blue['lines']['operations']), 2)
        self.assertEqual(report_blue['lines']['operations'][0]['bom_cost'], 40)
        self.assertEqual(report_blue['lines']['operations'][1]['bom_cost'], 120)

        report_green = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id, searchVariant=self.product_7_3.id)
        self.assertEqual(len(report_green['lines']['operations']), 1)
        self.assertEqual(report_green['lines']['operations'][0]['bom_cost'], 120)
