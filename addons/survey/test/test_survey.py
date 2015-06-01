# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class test_survey(common.TransactionCase):

    def setUp(self):
        super(test_survey, self).setUp()
        cr, uid, context = self.cr, self.uid, {}
        pass

    def test_00_create_survey_and_questions(self):
        cr, uid, context = self.cr, self.uid, {}
        pass

    def test_01_fill_survey(self):
        pass

    def test_02_answer_survey(self):
        pass
