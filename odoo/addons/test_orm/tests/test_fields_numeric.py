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

    def test_20_float(self):
        """ test rounding of float fields """
        record = self.env['test_orm.mixed'].create({})
        query = "SELECT 1 FROM test_orm_mixed WHERE id=%s AND number=%s"

        # 2.49609375 (exact float) must be rounded to 2.5
        record.write({'number': 2.49609375})
        self.env.flush_all()
        self.cr.execute(query, [record.id, '2.5'])
        self.assertTrue(self.cr.rowcount)
        self.assertEqual(record.number, 2.5)

        # 1.1 (1.1000000000000000888178420 in float) must be 1.1 in database
        record.write({'number': 1.1})
        self.env.flush_all()
        self.cr.execute(query, [record.id, '1.1'])
        self.assertTrue(self.cr.rowcount)
        self.assertEqual(record.number, 1.1)

    def test_21_float_digits(self):
        """ test field description """
        precision = self.env.ref('test_orm.decimal_orm_number')
        description = self.env['test_orm.mixed'].fields_get()['number2']
        self.assertEqual(description['digits'], (16, precision.digits))

    def check_monetary(self, record, amount, currency, msg=None):
        # determine the possible roundings of amount
        if currency:
            ramount = currency.round(amount)
            samount = float(float_repr(ramount, currency.decimal_places))
        else:
            ramount = samount = amount

        # check the currency on record
        self.assertEqual(record.currency_id, currency)

        # check the value on the record
        self.assertIn(record.amount, [ramount, samount], msg)

        # check the value in the database
        self.env.flush_all()
        self.cr.execute('SELECT amount FROM test_orm_mixed WHERE id=%s', [record.id])
        value = self.cr.fetchone()[0]
        self.assertEqual(value, samount, msg)

    def test_20_monetary(self):
        """ test monetary fields """
        model = self.env['test_orm.mixed']
        currency = self.env['res.currency'].with_context(active_test=False)
        amount = 14.70126

        for rounding in [0.01, 0.0001, 1.0, 0]:
            # first retrieve a currency corresponding to rounding
            if rounding:
                currency = currency.search([('rounding', '=', rounding)], limit=1)
                self.assertTrue(currency, "No currency found for rounding %s" % rounding)
            else:
                # rounding=0 corresponds to currency=False
                currency = currency.browse()

            # case 1: create with amount and currency
            record = model.create({'amount': amount, 'currency_id': currency.id})
            self.check_monetary(record, amount, currency, 'create(amount, currency)')

            # case 2: assign amount
            record.amount = 0
            record.amount = amount
            self.check_monetary(record, amount, currency, 'assign(amount)')

            # case 3: write with amount and currency
            record.write({'amount': 0, 'currency_id': False})
            record.write({'amount': amount, 'currency_id': currency.id})
            self.check_monetary(record, amount, currency, 'write(amount, currency)')

            # case 4: write with amount only
            record.write({'amount': 0})
            record.write({'amount': amount})
            self.check_monetary(record, amount, currency, 'write(amount)')

            # case 5: write with amount on several records
            records = record + model.create({'currency_id': currency.id})
            records.write({'amount': 0})
            records.write({'amount': amount})
            for record in records:
                self.check_monetary(record, amount, currency, 'multi write(amount)')

    def test_20_monetary_related(self):
        """ test value rounding with related currency """
        currency = self.env.ref('base.USD')
        monetary_base = self.env['test_orm.monetary_base'].create({
            'base_currency_id': currency.id,
        })
        monetary_related = self.env['test_orm.monetary_related'].create({
            'monetary_id': monetary_base.id,
            'total': 1 / 3,
        })
        self.env.cr.execute(
            "SELECT total FROM test_orm_monetary_related WHERE id=%s",
            monetary_related.ids,
        )
        [total] = self.env.cr.fetchone()
        self.assertEqual(total, .33)

    def test_93_monetary_related(self):
        """ Check the currency field on related monetary fields. """
        # check base field
        model = self.env['test_orm.monetary_base']
        field = model._fields['amount']
        self.assertEqual(field.get_currency_field(model), 'base_currency_id')

        # related fields must use the field 'currency_id' or 'x_currency_id'
        model = self.env['test_orm.monetary_related']
        field = model._fields['amount']
        self.assertEqual(field.related, 'monetary_id.amount')
        self.assertEqual(field.get_currency_field(model), 'currency_id')

        model = self.env['test_orm.monetary_custom']
        field = model._fields['x_amount']
        self.assertEqual(field.related, 'monetary_id.amount')
        self.assertEqual(field.get_currency_field(model), 'x_currency_id')

        # inherited field must use the same field as its parent field
        model = self.env['test_orm.monetary_inherits']
        field = model._fields['amount']
        self.assertEqual(field.related, 'monetary_id.amount')
        self.assertEqual(field.get_currency_field(model), 'base_currency_id')


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestMonetaryAccess(TransactionCaseWithUserDemo):

    def test_monetary_access_create(self):
        """Monetary fields that depend on compute/related currency
           have never really been supported by the ORM.
           However, most currency fields are related.
           This limitation can cause monetary fields to not be rounded,
           as well as trigger spurious ACL errors.
        """
        user_admin = self.env.ref("base.user_admin")
        user_demo = self.user_demo.with_user(user_admin)

        # this would raise without the fix introduced in this commit
        new_user = user_demo.copy({'monetary': 1 / 3})
        new_user.partner_id.company_id = new_user.company_id

        # The following is here to document how the ORM behaves, not really part of the test;
        # in particular these specific points highlight the discrepancy between what is sent
        # to the database and what we get on the ORM side.
        # (to be fair, these are pre-existing ORM limitations that should have been avoided
        # by using more careful field definitions and testing)
        self.assertEqual(new_user.currency_id.id, False,
                         "The cache contains the wrong value for currency.")
        self.assertEqual(new_user.monetary, 1 / 3,
                         "Because of previous point, no rounding was done.")

        self.env.invalidate_all()

        self.assertEqual(new_user.currency_id.rounding, 0.01,
                         "We now get the correct currency.")
        self.assertEqual(new_user.monetary, 0.33,
                         "The value was rounded when added to the cache.")
