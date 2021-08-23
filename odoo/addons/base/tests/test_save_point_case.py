# -*- coding: utf-8 -*-

from odoo.tests.common import SavepointCase, HTTPCase


class TestSavepointCase(SavepointCase, HTTPCase):

    @classmethod
    def setUpClass(cls):
        super(TestSavepointCase, cls).setUpClass()
        cls.env.ref('base.invalid_xml_id')

    def test_nothing(self):
        pass
