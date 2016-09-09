# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase


class InverseCase(TransactionCase):
    def test_constraint_check_after_inverse(self):
        """This should raise nothing."""
        record = self.env["test_new_api.inverse_required"].create({
            "name": "1 Hello",
            "required": True,
        })
        self.assertEqual(record.sequence, 1)
        self.assertEqual(record.reference, "Hello")
