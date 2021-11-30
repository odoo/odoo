# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import cloc
from odoo.addons.base.tests import test_cloc

class TestClocFields(test_cloc.TestClocCustomization):

    def test_fields_from_import_module(self):
        """
            Check that custom computed fields installed with an imported module
            is counted as customization
        """
        self.env['ir.module.module'].create({
            'name': 'imported_module',
            'state': 'installed',
            'imported': True,
        })
        f1 = self.create_field('x_imported_field')
        self.create_xml_id('import_field', f1.id, 'imported_module')
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('imported_module', 0), 1, 'Count fields with xml_id of imported module')
        f2 = self.create_field('x_base_field')
        self.create_xml_id('base_field', f2.id, 'base')
        cl = cloc.Cloc()
        cl.count_customization(self.env)
        self.assertEqual(cl.code.get('base', 0), 0, "Don't count fields from standard module")
