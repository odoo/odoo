# -*- coding: utf-8 -*-
# © 2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import TransactionCase


class TestDbFloat(TransactionCase):
    def test_dp_float(self):
        test_obj = self.env['decimal.precision.test'].create({})
        self.assertEqual(test_obj.float_nonstored_computed_2, .33)
        self.assertEqual(test_obj.float_nonstored_computed_v8, .33)
