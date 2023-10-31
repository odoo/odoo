# -*- coding: utf-8 -*-
"""
Tests the ability to update environmental information on various nodes (e.g.
change user, add context keys, ...)
"""
import os.path

from lxml import etree
from lxml.builder import E

from odoo.tests import common
from odoo.tools import config
from odoo.tools.convert import xml_import

odoo = E.odoo
data = E.data
record = E.record
field = E.field
function = E.function

class TestEnv(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self._importer = xml_import(self.env.cr, 'test_convert', None, 'init')

    def importer(self, doc):
        etree.RelaxNG(
            etree.parse(
                os.path.join(config['root_path'], 'import_xml.rng')
            )
        ).assert_(doc)
        self._importer.parse(doc)

    def test_uid_data_record(self):
        self.importer(
            odoo(
                record(
                    field("a", name="name"),
                    model="test_convert.usered",
                    id="test_convert.testing"
                ),
                uid="base.default_user"
            )
        )

        r = self.env.ref('test_convert.testing')
        self.assertEqual(r.name, 'a')
        self.assertEqual(r.create_uid, self.env.ref('base.default_user'))
        self.assertEqual(r.user_id, self.env.ref('base.default_user'))

    def test_uid_data_function(self):
        self.importer(
            odoo(
                function(
                    model="test_convert.usered",
                    name="create",
                    eval="[[{'name': 'b'}]]",
                ),
                uid="base.default_user"
            )
        )

        r = self.env['test_convert.usered'].search([])
        self.assertEqual(r.name, 'b')
        self.assertEqual(r.create_uid, self.env.ref('base.default_user'))
        self.assertEqual(r.user_id, self.env.ref('base.default_user'))

    def test_uid_record(self):
        self.importer(
            odoo(
                record(
                    field('c', name="name"),
                    model="test_convert.usered",
                    id="test_convert.testing",
                    uid="base.default_user"
                ),
                uid="base.user_root"
            )
        )

        r = self.env.ref('test_convert.testing')
        self.assertEqual(r.name, 'c')
        self.assertEqual(r.create_uid, self.env.ref('base.default_user'))
        self.assertEqual(r.user_id, self.env.ref('base.default_user'))


    def test_uid_function(self):
        self.importer(
            odoo(
                function(
                    model="test_convert.usered",
                    name="create",
                    uid="base.default_user",
                    eval="[[{'name': 'd'}]]"
                ),
                uid="base.user_root"
            )
        )
        r = self.env['test_convert.usered'].search([])
        self.assertEqual(r.name, 'd')
        self.assertEqual(r.create_uid, self.env.ref('base.default_user'))
        self.assertEqual(r.user_id, self.env.ref('base.default_user'))

    def test_context_data_function(self):
        self.env.user.tz = 'UTC'
        self.importer(
            odoo(
                function(
                    model="test_convert.usered",
                    name="create",
                    eval="[[{'name': 'e'}]]",
                ),
                context="{'tz': 'Asia/Kabul'}",
            )
        )
        r = self.env['test_convert.usered'].search([])
        self.assertEqual(r.name, 'e')
        self.assertEqual(r.tz, 'Asia/Kabul')

    def test_context_function(self):
        self.env.user.tz = 'UTC'
        self.importer(
            odoo(
                function(
                    model="test_convert.usered",
                    name="create",
                    context="{'tz': 'Pacific/Apia'}",
                    eval="[[{'name': 'e'}]]",
                ),
                context="{'tz': 'Asia/Kabul'}",
            )
        )
        r = self.env['test_convert.usered'].search([])
        self.assertEqual(r.name, 'e')
        self.assertEqual(r.tz, 'Pacific/Apia')

    def test_context_data_record(self):
        self.env.user.tz = 'UTC'
        self.importer(
            odoo(
                record(
                    field("f", name="name"),
                    model="test_convert.usered",
                ),
                context="{'tz': 'America/Knox_IN'}"
            )
        )
        r = self.env['test_convert.usered'].search([])
        self.assertEqual(r.name, 'f')
        self.assertEqual(r.tz, 'America/Knox_IN')

    def test_context_record(self):
        self.env.user.tz = 'UTC'
        self.importer(
            odoo(
                record(
                    field("f", name="name"),
                    model="test_convert.usered",
                    context="{'tz': 'America/Adak'}",
                ),
                context="{'tz': 'America/Knox_IN'}"
            )
        )
        r = self.env['test_convert.usered'].search([])
        self.assertEqual(r.name, 'f')
        self.assertEqual(r.tz, 'America/Adak')
