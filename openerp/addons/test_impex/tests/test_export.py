# -*- coding: utf-8 -*-
import itertools
import openerp.modules.registry
import openerp

from openerp.tests import common


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

    def export(self, value, fields=('value',), context=None):
        record = self.make(value)
        return record._BaseModel__export_rows([f.split('/') for f in fields])

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
            [[u'0']])

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
            [[u'0.0']])

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
            [[u'0.0']])

    def test_epsilon(self):
        """ epsilon gets sliced to 0 due to precision
        """
        self.assertEqual(
            self.export(0.000000000027),
            [[u'0.0']])

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
            [['']])
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
            [['']])
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
            [['']])
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
            [['']])
    def test_basic(self):
        self.assertEqual(
            self.export('2011-11-07'),
            [[u'2011-11-07']])

class test_datetime(CreatorCase):
    model_name = 'export.datetime'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [['']])
    def test_basic(self):
        self.assertEqual(
            self.export('2011-11-07 21:05:48'),
            [[u'2011-11-07 21:05:48']])
    def test_tz(self):
        """ Export ignores the timezone and always exports to UTC

        .. note:: on the other hand, export uses user lang for name_get
        """
        # NOTE: ignores user timezone, always exports to UTC
        self.assertEqual(
            self.export('2011-11-07 21:05:48', context={'tz': 'Pacific/Norfolk'}),
            [[u'2011-11-07 21:05:48']])

class test_selection(CreatorCase):
    model_name = 'export.selection'
    translations_fr = [
        ("Qux", "toto"),
        ("Bar", "titi"),
        ("Foo", "tete"),
    ]

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

    def test_localized_export(self):
        self.registry('res.lang').load_lang(self.cr, openerp.SUPERUSER_ID, 'fr_FR')
        Translations = self.registry('ir.translation')
        for source, value in self.translations_fr:
            Translations.create(self.cr, openerp.SUPERUSER_ID, {
                'name': 'export.selection,value',
                'lang': 'fr_FR',
                'type': 'selection',
                'src': source,
                'value': value
            })
        self.assertEqual(
            self.export(2, context={'lang': 'fr_FR'}),
            [[u'Bar']])

class test_selection_function(CreatorCase):
    model_name = 'export.selection.function'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [['']])

    def test_value(self):
        # FIXME: selection functions export the *value* itself
        self.assertEqual(
            self.export(1),
            [[1]])
        self.assertEqual(
            self.export(3),
            [[3]])
        # fucking hell
        self.assertEqual(
            self.export(0),
            [['']])

class test_m2o(CreatorCase):
    model_name = 'export.many2one'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [[False]])
    def test_basic(self):
        """ Exported value is the name_get of the related object
        """
        integer_id = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        name = dict(self.registry('export.integer').name_get(
            self.cr, openerp.SUPERUSER_ID,[integer_id]))[integer_id]
        self.assertEqual(
            self.export(integer_id),
            [[name]])
    def test_path(self):
        """ Can recursively export fields of m2o via path
        """
        integer_id = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        self.assertEqual(
            self.export(integer_id, fields=['value/.id', 'value/value']),
            [[unicode(integer_id), u'42']])
    def test_external_id(self):
        integer_id = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        # Expecting the m2o target model name in the external id,
        # not this model's name
        external_id = u'__export__.export_integer_%d' % integer_id
        self.assertEqual(
            self.export(integer_id, fields=['value/id']),
            [[external_id]])

class test_o2m(CreatorCase):
    model_name = 'export.one2many'
    commands = [
        (0, False, {'value': 4, 'str': 'record1'}),
        (0, False, {'value': 42, 'str': 'record2'}),
        (0, False, {'value': 36, 'str': 'record3'}),
        (0, False, {'value': 4, 'str': 'record4'}),
        (0, False, {'value': 13, 'str': 'record5'}),
    ]
    names = [
        u'export.one2many.child:%d' % d['value']
        for c, _, d in commands
    ]

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [[False]])

    def test_single(self):
        self.assertEqual(
            self.export([(0, False, {'value': 42})]),
            # name_get result
            [[u'export.one2many.child:42']])

    def test_single_subfield(self):
        self.assertEqual(
            self.export([(0, False, {'value': 42})],
                        fields=['value', 'value/value']),
            [[u'export.one2many.child:42', u'42']])

    def test_integrate_one_in_parent(self):
        self.assertEqual(
            self.export([(0, False, {'value': 42})],
                        fields=['const', 'value/value']),
            [[u'4', u'42']])

    def test_multiple_records(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value/value']),
            [
                [u'4', u'4'],
                [u'', u'42'],
                [u'', u'36'],
                [u'', u'4'],
                [u'', u'13'],
            ])

    def test_multiple_records_name(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value']),
            [[
                u'4', u','.join(self.names)
            ]])

    def test_multiple_records_id(self):
        export = self.export(self.commands, fields=['const', 'value/.id'])
        O2M_c = self.registry('export.one2many.child')
        ids = O2M_c.browse(self.cr, openerp.SUPERUSER_ID,
                           O2M_c.search(self.cr, openerp.SUPERUSER_ID, []))
        self.assertEqual(
            export,
            [
                ['4', str(ids[0].id)],
                ['', str(ids[1].id)],
                ['', str(ids[2].id)],
                ['', str(ids[3].id)],
                ['', str(ids[4].id)],
            ])

    def test_multiple_records_with_name_before(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value', 'value/value']),
            [[ # exports sub-fields of very first o2m
                u'4', u','.join(self.names), u'4'
            ]])

    def test_multiple_records_with_name_after(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value/value', 'value']),
            [ # completely ignores name_get request
                [u'4', u'4', ''],
                ['', u'42', ''],
                ['', u'36', ''],
                ['', u'4', ''],
                ['', u'13', ''],
            ])

    def test_multiple_subfields_neighbour(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value/str','value/value']),
            [
                [u'4', u'record1', u'4'],
                ['', u'record2', u'42'],
                ['', u'record3', u'36'],
                ['', u'record4', u'4'],
                ['', u'record5', u'13'],
            ])

    def test_multiple_subfields_separated(self):
        self.assertEqual(
            self.export(self.commands, fields=['value/str', 'const', 'value/value']),
            [
                [u'record1', u'4', u'4'],
                [u'record2', '', u'42'],
                [u'record3', '', u'36'],
                [u'record4', '', u'4'],
                [u'record5', '', u'13'],
            ])

class test_o2m_multiple(CreatorCase):
    model_name = 'export.one2many.multiple'

    def make(self, value=None, **values):
        if value is not None: values['value'] = value
        id = self.model.create(self.cr, openerp.SUPERUSER_ID, values)
        return self.model.browse(self.cr, openerp.SUPERUSER_ID, [id])[0]

    def export(self, value=None, fields=('child1', 'child2',), context=None, **values):
        record = self.make(value, **values)
        return record._BaseModel__export_rows([f.split('/') for f in fields])

    def test_empty(self):
        self.assertEqual(
            self.export(child1=False, child2=False),
            [[False, False]])

    def test_single_per_side(self):
        self.assertEqual(
            self.export(child1=False, child2=[(0, False, {'value': 42})]),
            [[False, u'export.one2many.child.2:42']])

        self.assertEqual(
            self.export(child1=[(0, False, {'value': 43})], child2=False),
            [[u'export.one2many.child.1:43', False]])

        self.assertEqual(
            self.export(child1=[(0, False, {'value': 43})],
                        child2=[(0, False, {'value': 42})]),
            [[u'export.one2many.child.1:43', u'export.one2many.child.2:42']])

    def test_single_integrate_subfield(self):
        fields = ['const', 'child1/value', 'child2/value']
        self.assertEqual(
            self.export(child1=False, child2=[(0, False, {'value': 42})],
                        fields=fields),
            [[u'36', False, u'42']])

        self.assertEqual(
            self.export(child1=[(0, False, {'value': 43})], child2=False,
                        fields=fields),
            [[u'36', u'43', False]])

        self.assertEqual(
            self.export(child1=[(0, False, {'value': 43})],
                        child2=[(0, False, {'value': 42})],
                        fields=fields),
            [[u'36', u'43', u'42']])

    def test_multiple(self):
        """ With two "concurrent" o2ms, exports the first line combined, then
        exports the rows for the first o2m, then the rows for the second o2m.
        """
        fields = ['const', 'child1/value', 'child2/value']
        child1 = [(0, False, {'value': v, 'str': 'record%.02d' % index})
                  for index, v in zip(itertools.count(), [4, 42, 36, 4, 13])]
        child2 = [(0, False, {'value': v, 'str': 'record%.02d' % index})
                  for index, v in zip(itertools.count(10), [8, 12, 8, 55, 33, 13])]

        self.assertEqual(
            self.export(child1=child1, child2=False, fields=fields),
            [
                [u'36', u'4', False],
                ['', u'42', ''],
                ['', u'36', ''],
                ['', u'4', ''],
                ['', u'13', ''],
            ])
        self.assertEqual(
            self.export(child1=False, child2=child2, fields=fields),
            [
                [u'36', False, u'8'],
                ['', '', u'12'],
                ['', '', u'8'],
                ['', '', u'55'],
                ['', '', u'33'],
                ['', '', u'13'],
            ])
        self.assertEqual(
            self.export(child1=child1, child2=child2, fields=fields),
            [
                [u'36', u'4', u'8'],
                ['', u'42', ''],
                ['', u'36', ''],
                ['', u'4', ''],
                ['', u'13', ''],
                ['', '', u'12'],
                ['', '', u'8'],
                ['', '', u'55'],
                ['', '', u'33'],
                ['', '', u'13'],
            ])

class test_m2m(CreatorCase):
    model_name = 'export.many2many'
    commands = [
        (0, False, {'value': 4, 'str': 'record000'}),
        (0, False, {'value': 42, 'str': 'record001'}),
        (0, False, {'value': 36, 'str': 'record010'}),
        (0, False, {'value': 4, 'str': 'record011'}),
        (0, False, {'value': 13, 'str': 'record100'}),
    ]
    names = [
        u'export.many2many.other:%d' % d['value']
        for c, _, d in commands
    ]

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [[False]])

    def test_single(self):
        self.assertEqual(
            self.export([(0, False, {'value': 42})]),
            # name_get result
            [[u'export.many2many.other:42']])

    def test_single_subfield(self):
        self.assertEqual(
            self.export([(0, False, {'value': 42})],
                        fields=['value', 'value/value']),
            [[u'export.many2many.other:42', u'42']])

    def test_integrate_one_in_parent(self):
        self.assertEqual(
            self.export([(0, False, {'value': 42})],
                        fields=['const', 'value/value']),
            [[u'4', u'42']])

    def test_multiple_records(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value/value']),
            [
                [u'4', u'4'],
                [u'', u'42'],
                [u'', u'36'],
                [u'', u'4'],
                [u'', u'13'],
            ])

    def test_multiple_records_name(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value']),
            [[ # FIXME: hardcoded comma, import uses config.csv_internal_sep
               # resolution: remove configurable csv_internal_sep
                u'4', u','.join(self.names)
            ]])

    # essentially same as o2m, so boring

class test_function(CreatorCase):
    model_name = 'export.function'

    def test_value(self):
        """ Exports value normally returned by accessing the function field
        """
        self.assertEqual(
            self.export(42),
            [[u'3']])
