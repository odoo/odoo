import base64
import io
from collections import OrderedDict
from datetime import date, datetime
from unittest.mock import patch
from contextlib import contextmanager

import psycopg2
from PIL import Image

from odoo import Command, fields, models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tests import TransactionCase, tagged, users
from odoo.tools import BinaryBytes, float_repr, mute_logger
from odoo.tools.image import binary_to_image, image_data_uri

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.base.tests.files import SVG_RAW, ZIP_RAW
from odoo.addons.test_orm.tests.test_domain_expression import TransactionExpressionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestFields(TransactionCaseWithUserDemo, TransactionExpressionCase):
    def setUp(self):
        # for tests methods that create custom models/fields
        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_all_caches)
        super().setUp()
        self.env.ref('test_orm.discussion_0').write({'participants': [Command.link(self.user_demo.id)]})
        # YTI FIX ME: The cache shouldn't be inconsistent (rco is gonna fix it)
        # self.env.ref('test_orm.discussion_0').participants -> 1 user
        # self.env.ref('test_orm.discussion_0').invalidate()
        # self.env.ref('test_orm.discussion_0').with_context(active_test=False).participants -> 2 users
        self.env.ref('test_orm.message_0_1').write({'author': self.user_demo.id})

    def test_21_date(self):
        """ test date fields """
        record = self.env['test_orm.mixed'].create({})

        # one may assign False or None
        record.date = None
        self.assertFalse(record.date)

        # one may assign date but not datetime objects
        record.date = date(2012, 5, 1)
        self.assertEqual(record.date, date(2012, 5, 1))

        # DLE P41: We now support to assign datetime to date. Not sure this is the good practice though.
        # with self.assertRaises(TypeError):
        #     record.date = datetime(2012, 5, 1, 10, 45, 0)

        # one may assign dates and datetime in the default format, and it must be checked
        record.date = '2012-05-01'
        self.assertEqual(record.date, date(2012, 5, 1))

        record.date = "2012-05-01 10:45:00"
        self.assertEqual(record.date, date(2012, 5, 1))

        with self.assertRaises(ValueError):
            record.date = '12-5-1'

        # check filtered_domain
        self.assertTrue(record.filtered_domain([('date', '<', '2012-05-02')]))
        self.assertTrue(record.filtered_domain([('date', '<', date(2012, 5, 2))]))
        self.assertTrue(record.filtered_domain([('date', '<', datetime(2012, 5, 2, 12, 0, 0))]))
        self.assertTrue(record.filtered_domain([('date', '!=', False)]))
        self.assertFalse(record.filtered_domain([('date', '=', False)]))

        record.date = None
        self.assertFalse(record.filtered_domain([('date', '<', '2012-05-02')]))
        self.assertFalse(record.filtered_domain([('date', '<', date(2012, 5, 2))]))
        self.assertFalse(record.filtered_domain([('date', '<', datetime(2012, 5, 2, 12, 0, 0))]))
        self.assertFalse(record.filtered_domain([('date', '!=', False)]))
        self.assertTrue(record.filtered_domain([('date', '=', False)]))

    def test_21_datetime(self):
        """ test datetime fields """
        for _i in range(0, 10):
            self.assertEqual(fields.Datetime.now().microsecond, 0)

        record = self.env['test_orm.mixed'].create({})

        # assign falsy value
        record.moment = None
        self.assertFalse(record.moment)

        # assign string
        record.moment = '2012-05-01'
        self.assertEqual(record.moment, datetime(2012, 5, 1))
        record.moment = '2012-05-01 06:00:00'
        self.assertEqual(record.moment, datetime(2012, 5, 1, 6))
        with self.assertRaises(ValueError):
            record.moment = '12-5-1'

        # assign date or datetime
        record.moment = date(2012, 5, 1)
        self.assertEqual(record.moment, datetime(2012, 5, 1))
        record.moment = datetime(2012, 5, 1, 6)
        self.assertEqual(record.moment, datetime(2012, 5, 1, 6))

        # check filtered_domain
        self.assertTrue(record.filtered_domain([('moment', '<', '2012-05-02')]))
        self.assertTrue(record.filtered_domain([('moment', '<', date(2012, 5, 2))]))
        self.assertTrue(record.filtered_domain([('moment', '<', datetime(2012, 5, 1, 12, 0, 0))]))
        self.assertTrue(record.filtered_domain([('moment', '!=', False)]))
        self.assertFalse(record.filtered_domain([('moment', '=', False)]))

        record.moment = None
        self.assertFalse(record.filtered_domain([('moment', '<', '2012-05-02')]))
        self.assertFalse(record.filtered_domain([('moment', '<', date(2012, 5, 2))]))
        self.assertFalse(record.filtered_domain([('moment', '<', datetime(2012, 5, 2, 12, 0, 0))]))
        self.assertFalse(record.filtered_domain([('moment', '!=', False)]))
        self.assertTrue(record.filtered_domain([('moment', '=', False)]))

    def test_21_date_dynamic(self):
        record = self.env['test_orm.mixed'].create({'moment': fields.Datetime.now()})
        self.assertEqual(record, self._search(record, [('moment', '<', 'now +1d')], [('id', 'in', record.ids)]))
        self.assertFalse(self._search(record, [('moment', '<', 'today')], [('id', 'in', record.ids)]))
        self.assertEqual(record, self._search(record, [('moment', '>', '-1H')], [('id', 'in', record.ids)]))
