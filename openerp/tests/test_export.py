# -*- coding: utf-8 -*-
import psycopg2

import openerp.modules.registry
import openerp
from openerp.osv import orm, fields

from . import common

models = [
    ('boolean', fields.boolean()),
    ('integer', fields.integer()),
    ('float', fields.float()),
    ('decimal', fields.float(digits=(16, 3))),
    ('string.bounded', fields.char('unknown', size=16)),
    ('string', fields.char('unknown', size=None)),
    ('date', fields.date()),
    ('datetime', fields.datetime()),
    ('text', fields.text()),
    ('selection', fields.selection([(1, "Foo"), (2, "Bar"), (3, "Qux")])),
    # TODO: m2o, o2m, m2m
    # TODO: function?
    # TODO: related?
    # TODO: reference?
]
for name, field in models:
    attrs = {
        '_name': 'export.%s' % name,
        '_module': 'base',
        '_columns': {
            'value': field
        }
    }
    NewModel = type(
        'Export%s' % ''.join(section.capitalize() for section in name.split('.')),
        (orm.Model,),
        attrs)

def setUpModule():
    openerp.tools.config['update'] = dict(base=1)
    openerp.modules.registry.RegistryManager.new(
        common.DB, update_module=True)

class CreatorCase(common.TransactionCase):
    model_name = False

    def __init__(self, *args, **kwargs):
        super(CreatorCase, self).__init__(*args, **kwargs)
        self.model = None

    def setUp(self):
        super(CreatorCase, self).setUp()
        self.model = self.registry(self.model_name)
    def make(self, value):
        id = self.model.create(self.cr, openerp.SUPERUSER_ID, {'value': value})
        return self.model.browse(self.cr, openerp.SUPERUSER_ID, [id])[0]
    def export(self, value, context=None):
        record = self.make(value)
        return self.model._BaseModel__export_row(
            self.cr, openerp.SUPERUSER_ID, record, [["value"]], context=context)

class test_boolean_field(CreatorCase):
    model_name = 'export.boolean'

    def test_true(self):
        self.assertEqual(
            self.export(True),
            [[u'True']])
    def test_false(self):
        """ ``False`` value to boolean fields is unique in being exported as a
        (unicode) string, not a boolean
        """
        self.assertEqual(
            self.export(False),
            [[u'False']])

class test_integer_field(CreatorCase):
    model_name = 'export.integer'

    def test_empty(self):
        self.assertEqual(self.model.search(self.cr, openerp.SUPERUSER_ID, []), [],
                         "Test model should have no records")
    def test_0(self):
        self.assertEqual(
            self.export(0),
            [[False]])

    def test_basic_value(self):
        self.assertEqual(
            self.export(42),
            [[u'42']])

    def test_negative(self):
        self.assertEqual(
            self.export(-32),
            [[u'-32']])

    def test_huge(self):
        self.assertEqual(
            self.export(2**31-1),
            [[unicode(2**31-1)]])

class test_float_field(CreatorCase):
    model_name = 'export.float'

    def test_0(self):
        self.assertEqual(
            self.export(0.0),
            [[False]])

    def test_epsilon(self):
        self.assertEqual(
            self.export(0.000000000027),
            [[u'2.7e-11']])

    def test_negative(self):
        self.assertEqual(
            self.export(-2.42),
            [[u'-2.42']])

    def test_positive(self):
        self.assertEqual(
            self.export(47.36),
            [[u'47.36']])

    def test_big(self):
        self.assertEqual(
            self.export(87654321.4678),
            [[u'87654321.4678']])

class test_decimal_field(CreatorCase):
    model_name = 'export.decimal'

    def test_0(self):
        self.assertEqual(
            self.export(0.0),
            [[False]])

    def test_epsilon(self):
        """ epsilon gets sliced to 0 due to precision
        """
        self.assertEqual(
            self.export(0.000000000027),
            [[False]])

    def test_negative(self):
        self.assertEqual(
            self.export(-2.42),
            [[u'-2.42']])

    def test_positive(self):
        self.assertEqual(
            self.export(47.36),
            [[u'47.36']])

    def test_big(self):
        self.assertEqual(
            self.export(87654321.4678), [[u'87654321.468']])

class test_string_field(CreatorCase):
    model_name = 'export.string.bounded'

    def test_empty(self):
        self.assertEqual(
            self.export(""),
            [[False]])
    def test_within_bounds(self):
        self.assertEqual(
            self.export("foobar"),
            [[u"foobar"]])
    def test_out_of_bounds(self):
        self.assertEqual(
            self.export("C for Sinking, "
                        "Java for Drinking, "
                        "Smalltalk for Thinking. "
                        "...and Power to the Penguin!"),
            [[u"C for Sinking, J"]])

class test_unbound_string_field(CreatorCase):
    model_name = 'export.string'

    def test_empty(self):
        self.assertEqual(
            self.export(""),
            [[False]])
    def test_small(self):
        self.assertEqual(
            self.export("foobar"),
            [[u"foobar"]])
    def test_big(self):
        self.assertEqual(
            self.export("We flew down weekly to meet with IBM, but they "
                        "thought the way to measure software was the amount "
                        "of code we wrote, when really the better the "
                        "software, the fewer lines of code."),
            [[u"We flew down weekly to meet with IBM, but they thought the "
              u"way to measure software was the amount of code we wrote, "
              u"when really the better the software, the fewer lines of "
              u"code."]])

class test_text(CreatorCase):
    model_name = 'export.text'

    def test_empty(self):
        self.assertEqual(
            self.export(""),
            [[False]])
    def test_small(self):
        self.assertEqual(
            self.export("foobar"),
            [[u"foobar"]])
    def test_big(self):
        self.assertEqual(
            self.export("So, `bind' is `let' and monadic programming is"
                        " equivalent to programming in the A-normal form. That"
                        " is indeed all there is to monads"),
            [[u"So, `bind' is `let' and monadic programming is equivalent to"
              u" programming in the A-normal form. That is indeed all there"
              u" is to monads"]])

class test_date(CreatorCase):
    model_name = 'export.date'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [[False]])
    def test_basic(self):
        self.assertEqual(
            self.export('2011-11-07'),
            [[u'2011-11-07']])

class test_datetime(CreatorCase):
    model_name = 'export.datetime'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [[False]])
    def test_basic(self):
        self.assertEqual(
            self.export('2011-11-07 21:05:48'),
            [[u'2011-11-07 21:05:48']])
    def test_tz(self):
        """ Export ignores the timezone and always exports to UTC
        """
        self.assertEqual(
            self.export('2011-11-07 21:05:48', {'tz': 'Pacific/Norfolk'}),
            [[u'2011-11-07 21:05:48']])

class test_selection(CreatorCase):
    model_name = 'export.selection'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [[False]])

    def test_value(self):
        """ selections export the *label* for their value
        """
        self.assertEqual(
            self.export(2),
            [[u"Bar"]])

