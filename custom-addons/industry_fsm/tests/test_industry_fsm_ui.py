# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

import logging

from odoo.tests import tagged, HttpCase, loaded_demo_data

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestIndustryFsmUi(HttpCase):
    def test_ui(self):
        self.env['res.partner'].create([
            {'name': 'Leroy Philippe', 'email': 'leroy.philou@example.com'},
            {'name': 'Brandon Freeman', 'email': 'brandon.freeman55@example.com'},
        ])
        self.start_tour("/web", 'industry_fsm_tour', login="admin")
        self.start_tour('/web', 'fsm_task_form_tour', login="admin")
