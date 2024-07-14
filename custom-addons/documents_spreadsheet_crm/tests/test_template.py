# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestSpreadsheetTemplate(HttpCase):

    def test_insert_pivot_in_spreadsheet(self):
        self.env['crm.lead'].create({
            'name': 'Test Lead',
            'user_id': self.env.ref('base.user_admin').id,
        })
        self.start_tour('/web', 'insert_crm_pivot_in_spreadsheet', login='admin')
