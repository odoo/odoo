# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestDeferredRevenue(common.TransactionCase):

    def test_print_survey(self):
        '''I print the survey to fill up the interview question'''

        self.env.ref('hr_recruitment.hr_case_programmer').action_print_survey()
