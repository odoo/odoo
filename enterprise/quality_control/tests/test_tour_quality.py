# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged
from odoo import Command
from .test_common import TestQualityCommon
from odoo.addons.spreadsheet_edition.tests.spreadsheet_test_case import SpreadsheetTestCase


@tagged('post_install', '-at_install')
class TestQualitySpreadsheetTemplate(HttpCase, TestQualityCommon, SpreadsheetTestCase):
    def test_create_new_spreadsheet_from_quality_form(self):
        spreadsheet_template = self.env['quality.spreadsheet.template'].create({
                'check_cell': 'A1',
                'name': 'my spreadsheet quality check template',
        })

        quality_point = self.env['quality.point'].create({
            'picking_type_ids': [
                Command.create({
                    'name': 'operation_test',
                    'sequence_code': 'MO2',
                })
            ],
            'test_type_id': self.env.ref('quality_control.test_type_spreadsheet').id,
            'spreadsheet_template_id': spreadsheet_template.id,
        })

        url = f"/odoo/{quality_point._name}/{quality_point.id}"
        self.start_tour(url, "test_create_new_spreadsheet_from_quality_form", login='admin')
