# -*- coding: utf-8 -*-

from openerp.tests import common
from openerp import models
import unittest2


class TestExportFields(unittest2.TestCase):
    def setUp(self):
        pass

    def test_field_o2o(self):
        self.assertEqual(models.export_fields_xml([[u'id'], [u'email']], [[u'base.res_partner_2', u'agrolait@yourcompany.example.com'], [u'base.res_partner_address_4', u'michel.fletcher@agrolait.example.com']]))

