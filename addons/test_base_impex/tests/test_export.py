# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import pstats
from cProfile import Profile

from odoo import fields
from odoo.tests import common


class CreatorCase(common.TransactionCase):
    model_name = False

    def __init__(self, *args, **kwargs):
        super(CreatorCase, self).__init__(*args, **kwargs)
        self.model = None

    def setUp(self):
        super(CreatorCase, self).setUp()
        self.model = self.env[self.model_name]

    def make(self, value, context=None):
        return self.model.with_context(**(context or {})).create({'value': value})

    def export(self, value, fields=('value',), context=None):
        record = self.make(value, context=context)
        record.invalidate_cache()
        return record._export_rows([f.split('/') for f in fields])

class test_xids(CreatorCase):
    model_name = 'export.boolean'

    def test_no_module(self):
        record = self.make(True)
        # add existing xid without module
        self.env['ir.model.data'].create({
            'module': '',
            'name': 'x',
            'model': self.model_name,
            'res_id': record.id,
        })
        record.invalidate_cache()
        self.assertEqual(
            record._export_rows([['id'], ['value']]),
            [[u'x', True]]
        )

class test_boolean_field(CreatorCase):
    model_name = 'export.boolean'

    def test_true(self):
        self.assertEqual(
            self.export(True),
            [[True]])

    def test_false(self):
        """ ``False`` value to boolean fields is unique in being exported as a
        (unicode) string, not a boolean
        """
        self.assertEqual(
            self.export(False),
            [[False]])


class test_integer_field(CreatorCase):
    model_name = 'export.integer'

    def test_empty(self):
        self.assertEqual(self.model.search([]).ids, [],
                         "Test model should have no records")

    def test_0(self):
        self.assertEqual(
            self.export(0),
            [[0]])

    def test_basic_value(self):
        self.assertEqual(
            self.export(42),
            [[42]])

    def test_negative(self):
        self.assertEqual(
            self.export(-32),
            [[-32]])

    def test_huge(self):
        self.assertEqual(
            self.export(2**31-1),
            [[2147483647]])


class test_float_field(CreatorCase):
    model_name = 'export.float'

    def test_0(self):
        self.assertEqual(
            self.export(0.0),
            [[0.0]])

    def test_epsilon(self):
        self.assertEqual(
            self.export(0.000000000027),
            [[0.000000000027]])

    def test_negative(self):
        self.assertEqual(
            self.export(-2.42),
            [[-2.42]])

    def test_positive(self):
        self.assertEqual(
            self.export(47.36),
            [[47.36]])

    def test_big(self):
        self.assertEqual(
            self.export(87654321.4678),
            [[87654321.4678]])


class test_decimal_field(CreatorCase):
    model_name = 'export.decimal'

    def test_0(self):
        self.assertEqual(
            self.export(0.0),
            [[0.0]])

    def test_epsilon(self):
        """ epsilon gets sliced to 0 due to precision
        """
        self.assertEqual(
            self.export(0.000000000027),
            [[0.0]])

    def test_negative(self):
        self.assertEqual(
            self.export(-2.42),
            [[-2.42]])

    def test_positive(self):
        self.assertEqual(
            self.export(47.36),
            [[47.36]])

    def test_big(self):
        self.assertEqual(
            self.export(87654321.4678), [[87654321.468]])


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

    def test_numeric(self):
        self.assertEqual(
            self.export(42),
            [["42"]])

class test_date(CreatorCase):
    model_name = 'export.date'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [['']])

    def test_basic(self):
        self.assertEqual(
            self.export('2011-11-07'),
            [[fields.Date.from_string('2011-11-07')]])


class test_datetime(CreatorCase):
    model_name = 'export.datetime'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [['']])

    def test_basic(self):
        """ Export value with no TZ set on the user
        """
        self.env.user.write({'tz': False})
        self.assertEqual(
            self.export('2011-11-07 21:05:48'),
            [[fields.Datetime.from_string('2011-11-07 21:05:48')]])

    def test_tz(self):
        """ Export converts the value in the user's TZ

        .. note:: on the other hand, export uses user lang for name_get
        """
        self.assertEqual(
            self.export('2011-11-07 21:05:48', context={'tz': 'Pacific/Norfolk'}),
            [[fields.Datetime.from_string('2011-11-08 08:35:48')]])


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
            [['']])

    def test_value(self):
        """ selections export the *label* for their value
        """
        self.assertEqual(
            self.export('2'),
            [[u"Bar"]])

    def test_localized_export(self):
        self.env['res.lang']._activate_lang('fr_FR')
        ir_field = self.env['ir.model.fields']._get('export.selection', 'value')
        selection = ir_field.selection_ids
        translations = dict(self.translations_fr)
        for sel_fr, sel in zip(selection.with_context(lang='fr_FR'), selection):
            sel_fr.name = translations.get(sel.name, sel_fr.name)
        self.assertEqual(
            self.export('2', context={'lang': 'fr_FR'}),
            [[u'titi']])


class test_selection_function(CreatorCase):
    model_name = 'export.selection.function'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [['']])

    def test_value(self):
        # selection functions export the *value* itself
        self.assertEqual(
            self.export('1'),
            [['1']])
        self.assertEqual(
            self.export('3'),
            [['3']])
        self.assertEqual(
            self.export('0'),
            [['0']])


class test_m2o(CreatorCase):
    model_name = 'export.many2one'

    def test_empty(self):
        self.assertEqual(
            self.export(False),
            [[False]])

    def test_basic(self):
        """ Exported value is the name_get of the related object
        """
        record = self.env['export.integer'].create({'value': 42})
        name = dict(record.name_get())[record.id]
        self.assertEqual(
            self.export(record.id),
            [[name]])

    def test_path(self):
        """ Can recursively export fields of m2o via path
        """
        record = self.env['export.integer'].create({'value': 42})
        self.assertEqual(
            self.export(record.id, fields=['value/.id', 'value/value']),
            [[str(record.id), 42]])

    def test_external_id(self):
        record = self.env['export.integer'].create({'value': 42})
        # Expecting the m2o target model name in the external id,
        # not this model's name
        self.assertRegex(
            self.export(record.id, fields=['value/id'])[0][0],
            u'__export__.export_integer_%d_[0-9a-f]{8}' % record.id)

    def test_identical(self):
        m2o = self.env['export.integer'].create({'value': 42}).id
        records = \
          ( self.make(m2o)
          | self.make(m2o)
          | self.make(m2o)
          | self.make(m2o)
        )
        records.invalidate_cache()
        xp = [r[0] for r in records._export_rows([['value', 'id']])]
        self.assertEqual(len(xp), 4)
        self.assertRegex(
            xp[0],
            u'__export__.export_integer_%d_[0-9a-f]{8}' % m2o
        )
        self.assertEqual(set(xp), {xp[0]})

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
            [[u'export.one2many.child:42', 42]])

    def test_integrate_one_in_parent(self):
        self.assertEqual(
            self.export([(0, False, {'value': 42})],
                        fields=['const', 'value/value']),
            [[4, 42]])

    def test_multiple_records(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value/value']),
            [
                [4, 4],
                [u'', 42],
                [u'', 36],
                [u'', 4],
                [u'', 13],
            ])

    def test_multiple_records_name(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value']),
            [
                [4, u'export.one2many.child:4'],
                [u'', u'export.one2many.child:42'],
                [u'', u'export.one2many.child:36'],
                [u'', u'export.one2many.child:4'],
                [u'', u'export.one2many.child:13'],
            ])

    def test_multiple_records_id(self):
        export = self.export(self.commands, fields=['const', 'value/.id'])
        records = self.env['export.one2many.child'].search([])
        self.assertEqual(
            export,
            [
                [4, str(records[0].id)],
                ['', str(records[1].id)],
                ['', str(records[2].id)],
                ['', str(records[3].id)],
                ['', str(records[4].id)],
            ])

    def test_multiple_records_with_name_before(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value', 'value/value']),
            [
                [4, u'export.one2many.child:4', 4],
                ['', u'export.one2many.child:42', 42],
                ['', u'export.one2many.child:36', 36],
                ['', u'export.one2many.child:4', 4],
                ['', u'export.one2many.child:13', 13],
            ])

    def test_multiple_records_with_name_after(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value/value', 'value']),
            [
                [4, 4, u'export.one2many.child:4'],
                ['', 42, u'export.one2many.child:42'],
                ['', 36, u'export.one2many.child:36'],
                ['', 4, u'export.one2many.child:4'],
                ['', 13, u'export.one2many.child:13'],
            ])

    def test_multiple_subfields_neighbour(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value/str','value/value']),
            [
                [4, u'record1', 4],
                ['', u'record2', 42],
                ['', u'record3', 36],
                ['', u'record4', 4],
                ['', u'record5', 13],
            ])

    def test_multiple_subfields_separated(self):
        self.assertEqual(
            self.export(self.commands, fields=['value/str', 'const', 'value/value']),
            [
                [u'record1', 4, 4],
                [u'record2', '', 42],
                [u'record3', '', 36],
                [u'record4', '', 4],
                [u'record5', '', 13],
            ])


class test_o2m_multiple(CreatorCase):
    model_name = 'export.one2many.multiple'

    def make(self, value=None, **values):
        if value is not None:
            values['value'] = value
        return self.model.create(values)

    def export(self, value=None, fields=('child1', 'child2',), context=None, **values):
        record = self.make(value, **values)
        return record._export_rows([f.split('/') for f in fields])

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
            [[36, False, 42]])

        self.assertEqual(
            self.export(child1=[(0, False, {'value': 43})], child2=False,
                        fields=fields),
            [[36, 43, False]])

        self.assertEqual(
            self.export(child1=[(0, False, {'value': 43})],
                        child2=[(0, False, {'value': 42})],
                        fields=fields),
            [[36, 43, 42]])

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
                [36, 4, False],
                ['', 42, ''],
                ['', 36, ''],
                ['', 4, ''],
                ['', 13, ''],
            ])
        self.assertEqual(
            self.export(child1=False, child2=child2, fields=fields),
            [
                [36, False, 8],
                ['', '', 12],
                ['', '', 8],
                ['', '', 55],
                ['', '', 33],
                ['', '', 13],
            ])
        self.assertEqual(
            self.export(child1=child1, child2=child2, fields=fields),
            [
                [36, 4, 8],
                ['', 42, ''],
                ['', 36, ''],
                ['', 4, ''],
                ['', 13, ''],
                ['', '', 12],
                ['', '', 8],
                ['', '', 55],
                ['', '', 33],
                ['', '', 13],
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
                        fields=['value', 'value/value'],
                        context={'import_compat': False}),
            [[u'export.many2many.other:42', 42]])

    def test_integrate_one_in_parent(self):
        self.assertEqual(
            self.export([(0, False, {'value': 42})],
                        fields=['const', 'value/value'],
                        context={'import_compat': False}),
            [[4, 42]])

    def test_multiple_records(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value/value'], context={'import_compat': False}),
            [
                [4, 4],
                [u'', 42],
                [u'', 36],
                [u'', 4],
                [u'', 13],
            ])

    def test_multiple_records_name(self):
        self.assertEqual(
            self.export(self.commands, fields=['const', 'value']),
            [
                [4, 'export.many2many.other:4,export.many2many.other:42,export.many2many.other:36,export.many2many.other:4,export.many2many.other:13'],
            ])

        self.assertEqual(
            self.export(self.commands, fields=['const', 'value'], context={'import_compat': False}),
            [
                [4, u'export.many2many.other:4'],
                ['', u'export.many2many.other:42'],
                ['', u'export.many2many.other:36'],
                ['', u'export.many2many.other:4'],
                ['', u'export.many2many.other:13'],
            ])

    def test_multiple_records_subfield(self):
        r = self.make(self.commands)
        xid = self.env['ir.model.data'].create({
            'name': 'whopwhopwhop',
            'module': '__t__',
            'model': r._name,
            'res_id': r.id,
        }).complete_name
        sids = [
            self.env['ir.model.data'].create({
                'name': sub.str,
                'module': '__t__',
                'model': sub._name,
                'res_id': sub.id,
            }).complete_name
            for sub in r.value
        ]
        r.invalidate_cache()

        self.assertEqual(
            r._export_rows([['value', 'id']]),
            [['__t__.record000,__t__.record001,__t__.record010,__t__.record011,__t__.record100']]
        )
        self.assertEqual(
            r.with_context(import_compat=True)._export_rows([['value', 'id']]),
            [['__t__.record000,__t__.record001,__t__.record010,__t__.record011,__t__.record100']]
        )
        self.assertEqual(
            r.with_context(import_compat=True)._export_rows([['value'], ['value', 'id']]),
            [['', '__t__.record000,__t__.record001,__t__.record010,__t__.record011,__t__.record100']]
        )

        self.assertEqual(
            r.with_context(import_compat=False)._export_rows([['id'], ['value', 'id'], ['value', 'value']]),
            [
                [xid, u'__t__.record000', 4],
                [u'', u'__t__.record001', 42],
                [u'', u'__t__.record010', 36],
                [u'', u'__t__.record011', 4],
                [u'', u'__t__.record100', 13]
            ]
        )
        self.assertEqual(
            r.with_context(import_compat=False)._export_rows([['id'], ['value', 'value'], ['value', 'id']]),
            [
                [xid, 4, u'__t__.record000'],
                [u'', 42, u'__t__.record001'],
                [u'', 36, u'__t__.record010'],
                [u'', 4, u'__t__.record011'],
                [u'', 13, u'__t__.record100']
            ]
        )


class test_function(CreatorCase):
    model_name = 'export.function'

    def test_value(self):
        """ Exports value normally returned by accessing the function field
        """
        self.assertEqual(
            self.export(42),
            [[3]])


@common.tagged('-standard', 'bench')
class test_xid_perfs(common.TransactionCase):
    def setUp(self):
        super(test_xid_perfs, self).setUp()

        self.profile = Profile()
        @self.addCleanup
        def _dump():
            stats = pstats.Stats(self.profile)
            stats.strip_dirs()
            stats.sort_stats('cumtime')
            stats.print_stats(20)
            self.profile = None

    def test_basic(self):
        Model = self.env['export.integer']
        for i in range(10000):
            Model.create({'value': i})
        Model.invalidate_cache()
        records = Model.search([])

        self.profile.runcall(records._export_rows, [['id'], ['value']])

    def test_m2o_single(self):
        rid = self.env['export.integer'].create({'value': 42}).id
        Model = self.env['export.many2one']
        for _ in range(10000):
            Model.create({'value': rid})
        Model.invalidate_cache()
        records = Model.search([])

        self.profile.runcall(records._export_rows, [['id'], ['value','id']])

    def test_m2o_each(self):
        Model = self.env['export.many2one']
        Integer = self.env['export.integer']
        for i in range(10000):
            Model.create({
                'value': Integer.create({'value': i}).id
            })
        Model.invalidate_cache()
        records = Model.search([])

        self.profile.runcall(records._export_rows, [['id'], ['value', 'id']])
