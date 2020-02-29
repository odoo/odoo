# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common

class TestBasicInheritance(common.TransactionCase):
    def test_extend_fields(self):
        env = self.env

        record = env['extension.0'].create({})

        reference =\
        {'name': "A", 'description': "Extended"}
        values =\
        record.read()[0]

        self.assertLess(reference.items(), values.items())
