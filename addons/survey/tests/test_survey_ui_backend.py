# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestUi(HttpCase):

    def test_tour_test_survey_form_triggers(self):
        self.start_tour('/odoo', 'survey_tour_test_survey_form_triggers', login='admin')
