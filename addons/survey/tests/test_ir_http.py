# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestIrHttp(TransactionCase):
    def test_is_survey_frontend(self):
        IrHttp = self.env['ir.http']
        self.assertTrue(IrHttp._is_survey_frontend('/survey/test'))
        self.assertTrue(IrHttp._is_survey_frontend('/fr_BE/survey/test'))
        self.assertTrue(IrHttp._is_survey_frontend('/fr/survey/test'))
        self.assertTrue(IrHttp._is_survey_frontend('/hr/survey/test'))  # we can't avoid that (hr is a language anyway)
        self.assertFalse(IrHttp._is_survey_frontend('/hr/event/test'))
        self.assertFalse(IrHttp._is_survey_frontend('/event'))
        self.assertFalse(IrHttp._is_survey_frontend('/event/survey/test'))
        self.assertFalse(IrHttp._is_survey_frontend('/eveNT/survey/test'))
        self.assertFalse(IrHttp._is_survey_frontend('/fr_BE/event/test'))
        self.assertFalse(IrHttp._is_survey_frontend('/fr/event/test'))
