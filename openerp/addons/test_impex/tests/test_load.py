# -*- coding: utf-8 -*-
import json
import pkgutil
import unittest

import openerp.modules.registry
import openerp

from openerp.tests import common
from openerp.tools.misc import mute_logger

def message(msg, type='error', from_=0, to_=0, record=0, field='value', **kwargs):
    return dict(kwargs,
                type=type, rows={'from': from_, 'to': to_}, record=record,
                field=field, message=msg)
def moreaction(**kwargs):
    return dict(kwargs,
        type='ir.actions.act_window',
        target='new',
        view_mode='tree,form',
        view_type='form',
        views=[(False, 'tree'), (False, 'form')],
        help=u"See all possible values")

def values(seq, field='value'):
    return [item[field] for item in seq]

class ImporterCase(common.TransactionCase):
    model_name = False

    def __init__(self, *args, **kwargs):
        super(ImporterCase, self).__init__(*args, **kwargs)
        self.model = None

    def setUp(self):
        super(ImporterCase, self).setUp()
        self.model = self.registry(self.model_name)
        self.registry('ir.model.data').clear_caches()

    def import_(self, fields, rows, context=None):
        return self.model.load(
            self.cr, openerp.SUPERUSER_ID, fields, rows, context=context)
    def read(self, fields=('value',), domain=(), context=None):
        return self.model.read(
            self.cr, openerp.SUPERUSER_ID,
            self.model.search(self.cr, openerp.SUPERUSER_ID, domain, context=context),
            fields=fields, context=context)
    def browse(self, domain=(), context=None):
        return self.model.browse(
            self.cr, openerp.SUPERUSER_ID,
            self.model.search(self.cr, openerp.SUPERUSER_ID, domain, context=context),
            context=context)

    def xid(self, record):
        ModelData = self.registry('ir.model.data')

        ids = ModelData.search(
            self.cr, openerp.SUPERUSER_ID,
            [('model', '=', record._name), ('res_id', '=', record.id)])
        if ids:
            d = ModelData.read(
                self.cr, openerp.SUPERUSER_ID, ids, ['name', 'module'])[0]
            if d['module']:
                return '%s.%s' % (d['module'], d['name'])
            return d['name']

        name = record.name_get()[0][1]
        # fix dotted name_get results, otherwise xid lookups blow up
        name = name.replace('.', '-')
        ModelData.create(self.cr, openerp.SUPERUSER_ID, {
            'name': name,
            'model': record._name,
            'res_id': record.id,
            'module': '__test__'
        })
        return '__test__.' + name

    def add_translations(self, name, type, code, *tnx):
        self.registry('res.lang').load_lang(self.cr, openerp.SUPERUSER_ID, code)
        Translations = self.registry('ir.translation')
        for source, value in tnx:
            Translations.create(self.cr, openerp.SUPERUSER_ID, {
                'name': name,
                'lang': code,
                'type': type,
                'src': source,
                'value': value,
                'state': 'translated',
            })

class test_ids_stuff(ImporterCase):
    model_name = 'export.integer'

    def test_create_with_id(self):
        result = self.import_(['.id', 'value'], [['42', '36']])
        self.assertIs(result['ids'], False)
        self.assertEqual(result['messages'], [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'field': '.id',
            'message': u"Unknown database identifier '42'",
        }])
    def test_create_with_xid(self):
        result = self.import_(['id', 'value'], [['somexmlid', '42']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])
        self.assertEqual(
            'somexmlid',
            self.xid(self.browse()[0]))

    def test_update_with_id(self):
        id = self.model.create(self.cr, openerp.SUPERUSER_ID, {'value': 36})
        self.assertEqual(
            36,
            self.model.browse(self.cr, openerp.SUPERUSER_ID, id).value)

        result = self.import_(['.id', 'value'], [[str(id), '42']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])
        self.assertEqual(
            [42], # updated value to imported
            values(self.read()))

    def test_update_with_xid(self):
        self.import_(['id', 'value'], [['somexmlid', '36']])
        self.assertEqual([36], values(self.read()))

        self.import_(['id', 'value'], [['somexmlid', '1234567']])
        self.assertEqual([1234567], values(self.read()))

class test_boolean_field(ImporterCase):
    model_name = 'export.boolean'

    def test_empty(self):
        self.assertEqual(
            self.import_(['value'], []),
            {'ids': [], 'messages': []})

    def test_exported(self):
        result = self.import_(['value'], [['False'], ['True'], ])
        self.assertEqual(len(result['ids']), 2)
        self.assertFalse(result['messages'])
        records = self.read()
        self.assertEqual([
            False,
            True,
        ], values(records))

    def test_falses(self):
        for lang, source, value in [('fr_FR', 'no', u'non'),
                                    ('de_DE', 'no', u'nein'),
                                    ('ru_RU', 'no', u'нет'),
                                    ('nl_BE', 'false', u'vals'),
                                    ('lt_LT', 'false', u'klaidingas')]:
            self.add_translations('test_import.py', 'code', lang, (source, value))
        falses = [[u'0'], [u'no'], [u'false'], [u'FALSE'], [u''],
                  [u'non'], # no, fr
                  [u'nein'], # no, de
                  [u'нет'], # no, ru
                  [u'vals'], # false, nl
                  [u'klaidingas'], # false, lt,
        ]

        result = self.import_(['value'], falses)
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), len(falses))
        self.assertEqual([False] * len(falses), values(self.read()))

    def test_trues(self):
        trues = [['None'], ['nil'], ['()'], ['f'], ['#f'],
                  # Problem: OpenOffice (and probably excel) output localized booleans
                  ['VRAI'], ['ok'], ['true'], ['yes'], ['1'], ]
        result = self.import_(['value'], trues)
        self.assertEqual(len(result['ids']), 10)
        self.assertEqual(result['messages'], [
            message(u"Unknown value '%s' for boolean field 'unknown', assuming 'yes'" % v[0],
                    moreinfo=u"Use '1' for yes and '0' for no",
                    type='warning', from_=i, to_=i, record=i)
            for i, v in enumerate(trues)
            if v[0] not in ('true', 'yes', '1')
        ])
        self.assertEqual(
            [True] * 10,
            values(self.read()))

class test_integer_field(ImporterCase):
    model_name = 'export.integer'

    def test_none(self):
        self.assertEqual(
            self.import_(['value'], []),
            {'ids': [], 'messages': []})

    def test_empty(self):
        result = self.import_(['value'], [['']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])
        self.assertEqual(
            [False],
            values(self.read()))

    def test_zero(self):
        result = self.import_(['value'], [['0']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])

        result = self.import_(['value'], [['-0']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])

        self.assertEqual([False, False], values(self.read()))

    def test_positives(self):
        result = self.import_(['value'], [
            ['1'],
            ['42'],
            [str(2**31-1)],
            ['12345678']
        ])
        self.assertEqual(len(result['ids']), 4)
        self.assertFalse(result['messages'])

        self.assertEqual([
            1, 42, 2**31-1, 12345678
        ], values(self.read()))

    def test_negatives(self):
        result = self.import_(['value'], [
            ['-1'],
            ['-42'],
            [str(-(2**31 - 1))],
            [str(-(2**31))],
            ['-12345678']
        ])
        self.assertEqual(len(result['ids']), 5)
        self.assertFalse(result['messages'])
        self.assertEqual([
            -1, -42, -(2**31 - 1), -(2**31), -12345678
        ], values(self.read()))

    @mute_logger('openerp.sql_db', 'openerp.models')
    def test_out_of_range(self):
        result = self.import_(['value'], [[str(2**31)]])
        self.assertIs(result['ids'], False)
        self.assertEqual(result['messages'], [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'message': "integer out of range\n"
        }])

        result = self.import_(['value'], [[str(-2**32)]])
        self.assertIs(result['ids'], False)
        self.assertEqual(result['messages'], [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'message': "integer out of range\n"
        }])

    def test_nonsense(self):
        result = self.import_(['value'], [['zorglub']])
        self.assertIs(result['ids'], False)
        self.assertEqual(result['messages'], [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'field': 'value',
            'message': u"'zorglub' does not seem to be an integer for field 'unknown'",
        }])

class test_float_field(ImporterCase):
    model_name = 'export.float'
    def test_none(self):
        self.assertEqual(
            self.import_(['value'], []),
            {'ids': [], 'messages': []})

    def test_empty(self):
        result = self.import_(['value'], [['']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])
        self.assertEqual(
            [False],
            values(self.read()))

    def test_zero(self):
        result = self.import_(['value'], [['0']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])

        result = self.import_(['value'], [['-0']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])

        self.assertEqual([False, False], values(self.read()))

    def test_positives(self):
        result = self.import_(['value'], [
            ['1'],
            ['42'],
            [str(2**31-1)],
            ['12345678'],
            [str(2**33)],
            ['0.000001'],
        ])
        self.assertEqual(len(result['ids']), 6)
        self.assertFalse(result['messages'])

        self.assertEqual([
            1, 42, 2**31-1, 12345678, 2.0**33, .000001
        ], values(self.read()))

    def test_negatives(self):
        result = self.import_(['value'], [
            ['-1'],
            ['-42'],
            [str(-2**31 + 1)],
            [str(-2**31)],
            ['-12345678'],
            [str(-2**33)],
            ['-0.000001'],
        ])
        self.assertEqual(len(result['ids']), 7)
        self.assertFalse(result['messages'])
        self.assertEqual([
            -1, -42, -(2**31 - 1), -(2**31), -12345678, -2.0**33, -.000001
        ], values(self.read()))

    def test_nonsense(self):
        result = self.import_(['value'], [['foobar']])
        self.assertIs(result['ids'], False)
        self.assertEqual(result['messages'], [
            message(u"'foobar' does not seem to be a number for field 'unknown'")])

class test_string_field(ImporterCase):
    model_name = 'export.string.bounded'

    def test_empty(self):
        result = self.import_(['value'], [['']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])
        self.assertEqual([False], values(self.read()))

    def test_imported(self):
        result = self.import_(['value'], [
            [u'foobar'],
            [u'foobarbaz'],
            [u'Með suð í eyrum við spilum endalaust'],
            [u"People 'get' types. They use them all the time. Telling "
             u"someone he can't pound a nail with a banana doesn't much "
             u"surprise him."]
        ])
        self.assertEqual(len(result['ids']), 4)
        self.assertFalse(result['messages'])
        self.assertEqual([
            u"foobar",
            u"foobarbaz",
            u"Með suð í eyrum ",
            u"People 'get' typ",
        ], values(self.read()))

class test_unbound_string_field(ImporterCase):
    model_name = 'export.string'

    def test_imported(self):
        result = self.import_(['value'], [
            [u'í dag viðrar vel til loftárása'],
            # ackbar.jpg
            [u"If they ask you about fun, you tell them – fun is a filthy"
             u" parasite"]
        ])
        self.assertEqual(len(result['ids']), 2)
        self.assertFalse(result['messages'])
        self.assertEqual([
            u"í dag viðrar vel til loftárása",
            u"If they ask you about fun, you tell them – fun is a filthy parasite"
        ], values(self.read()))

class test_required_string_field(ImporterCase):
    model_name = 'export.string.required'

    @mute_logger('openerp.sql_db', 'openerp.models')
    def test_empty(self):
        result = self.import_(['value'], [[]])
        self.assertEqual(result['messages'], [message(
            u"Missing required value for the field 'unknown' (value)")])
        self.assertIs(result['ids'], False)

    @mute_logger('openerp.sql_db', 'openerp.models')
    def test_not_provided(self):
        result = self.import_(['const'], [['12']])
        self.assertEqual(result['messages'], [message(
            u"Missing required value for the field 'unknown' (value)")])
        self.assertIs(result['ids'], False)

class test_text(ImporterCase):
    model_name = 'export.text'

    def test_empty(self):
        result = self.import_(['value'], [['']])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])
        self.assertEqual([False], values(self.read()))

    def test_imported(self):
        s = (u"Breiðskífa er notað um útgefna hljómplötu sem inniheldur "
             u"stúdíóupptökur frá einum flytjanda. Breiðskífur eru oftast "
             u"milli 25-80 mínútur og er lengd þeirra oft miðuð við 33⅓ "
             u"snúninga 12 tommu vínylplötur (sem geta verið allt að 30 mín "
             u"hvor hlið).\n\nBreiðskífur eru stundum tvöfaldar og eru þær þá"
             u" gefnar út á tveimur geisladiskum eða tveimur vínylplötum.")
        result = self.import_(['value'], [[s]])
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])
        self.assertEqual([s], values(self.read()))

class test_selection(ImporterCase):
    model_name = 'export.selection'
    translations_fr = [
        ("Foo", "tete"),
        ("Bar", "titi"),
        ("Qux", "toto"),
    ]

    def test_imported(self):
        result = self.import_(['value'], [
            ['Qux'],
            ['Bar'],
            ['Foo'],
            ['2'],
        ])
        self.assertEqual(len(result['ids']), 4)
        self.assertFalse(result['messages'])
        self.assertEqual([3, 2, 1, 2], values(self.read()))

    def test_imported_translated(self):
        self.add_translations(
            'export.selection,value', 'selection', 'fr_FR', *self.translations_fr)

        result = self.import_(['value'], [
            ['toto'],
            ['tete'],
            ['titi'],
        ], context={'lang': 'fr_FR'})
        self.assertEqual(len(result['ids']), 3)
        self.assertFalse(result['messages'])

        self.assertEqual([3, 1, 2], values(self.read()))

        result = self.import_(['value'], [['Foo']], context={'lang': 'fr_FR'})
        self.assertEqual(len(result['ids']), 1)
        self.assertFalse(result['messages'])

    def test_invalid(self):
        result = self.import_(['value'], [['Baz']])
        self.assertIs(result['ids'], False)
        self.assertEqual(result['messages'], [message(
            u"Value 'Baz' not found in selection field 'unknown'",
            moreinfo="Foo Bar Qux 4".split())])

        result = self.import_(['value'], [[42]])
        self.assertIs(result['ids'], False)
        self.assertEqual(result['messages'], [message(
            u"Value '42' not found in selection field 'unknown'",
            moreinfo="Foo Bar Qux 4".split())])

class test_selection_with_default(ImporterCase):
    model_name = 'export.selection.withdefault'

    def test_empty(self):
        """ Empty cells should set corresponding field to False
        """
        result = self.import_(['value'], [['']])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        self.assertEqual(
            values(self.read()),
            [False])

    def test_default(self):
        """ Non-provided cells should set corresponding field to default
        """
        result = self.import_(['const'], [['42']])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        self.assertEqual(
            values(self.read()),
            [2])

class test_selection_function(ImporterCase):
    model_name = 'export.selection.function'
    translations_fr = [
        ("Corge", "toto"),
        ("Grault", "titi"),
        ("Wheee", "tete"),
        ("Moog", "tutu"),
    ]

    def test_imported(self):
        """ import uses fields_get, so translates import label (may or may not
        be good news) *and* serializes the selection function to reverse it:
        import does not actually know that the selection field uses a function
        """
        # NOTE: conflict between a value and a label => pick first
        result = self.import_(['value'], [
            ['3'],
            ["Grault"],
        ])
        self.assertEqual(len(result['ids']), 2)
        self.assertFalse(result['messages'])
        self.assertEqual(
            [3, 1],
            values(self.read()))

    def test_translated(self):
        """ Expects output of selection function returns translated labels
        """
        self.add_translations(
            'export.selection,value', 'selection', 'fr_FR', *self.translations_fr)

        result = self.import_(['value'], [
            ['titi'],
            ['tete'],
        ], context={'lang': 'fr_FR'})
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 2)
        self.assertEqual(values(self.read()), [1, 2])

        result = self.import_(['value'], [['Wheee']], context={'lang': 'fr_FR'})
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

class test_m2o(ImporterCase):
    model_name = 'export.many2one'

    def test_by_name(self):
        # create integer objects
        integer_id1 = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        integer_id2 = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 36})
        # get its name
        name1 = dict(self.registry('export.integer').name_get(
            self.cr, openerp.SUPERUSER_ID,[integer_id1]))[integer_id1]
        name2 = dict(self.registry('export.integer').name_get(
            self.cr, openerp.SUPERUSER_ID,[integer_id2]))[integer_id2]

        result = self.import_(['value'], [
            # import by name_get
            [name1],
            [name1],
            [name2],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 3)
        # correct ids assigned to corresponding records
        self.assertEqual([
            (integer_id1, name1),
            (integer_id1, name1),
            (integer_id2, name2),],
            values(self.read()))

    def test_by_xid(self):
        ExportInteger = self.registry('export.integer')
        integer_id = ExportInteger.create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        xid = self.xid(ExportInteger.browse(
            self.cr, openerp.SUPERUSER_ID, [integer_id])[0])

        result = self.import_(['value/id'], [[xid]])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)
        b = self.browse()
        self.assertEqual(42, b[0].value.value)

    def test_by_id(self):
        integer_id = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        result = self.import_(['value/.id'], [[integer_id]])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)
        b = self.browse()
        self.assertEqual(42, b[0].value.value)

    def test_by_names(self):
        integer_id1 = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        integer_id2 = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        name1 = dict(self.registry('export.integer').name_get(
            self.cr, openerp.SUPERUSER_ID,[integer_id1]))[integer_id1]
        name2 = dict(self.registry('export.integer').name_get(
            self.cr, openerp.SUPERUSER_ID,[integer_id2]))[integer_id2]
        # names should be the same
        self.assertEqual(name1, name2)

        result = self.import_(['value'], [[name2]])
        self.assertEqual(
            result['messages'],
            [message(u"Found multiple matches for field 'unknown' (2 matches)",
                     type='warning')])
        self.assertEqual(len(result['ids']), 1)
        self.assertEqual([
            (integer_id1, name1)
        ], values(self.read()))

    def test_fail_by_implicit_id(self):
        """ Can't implicitly import records by id
        """
        # create integer objects
        integer_id1 = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        integer_id2 = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 36})

        # Because name_search all the things. Fallback schmallback
        result = self.import_(['value'], [
                # import by id, without specifying it
                [integer_id1],
                [integer_id2],
                [integer_id1],
        ])
        self.assertEqual(result['messages'], [
            message(u"No matching record found for name '%s' in field 'unknown'" % id,
                    from_=index, to_=index, record=index,
                    moreinfo=moreaction(res_model='export.integer'))
            for index, id in enumerate([integer_id1, integer_id2, integer_id1])])
        self.assertIs(result['ids'], False)

    @mute_logger('openerp.sql_db')
    def test_fail_id_mistype(self):
        result = self.import_(['value/.id'], [["foo"]])

        self.assertEqual(result['messages'], [
            message(u"Invalid database id 'foo' for the field 'unknown'",
                    moreinfo=moreaction(res_model='ir.model.data',
                                        domain=[('model','=','export.integer')]))
        ])
        self.assertIs(result['ids'], False)

    def test_sub_field(self):
        """ Does not implicitly create the record, does not warn that you can't
        import m2o subfields (at all)...
        """
        result = self.import_(['value/value'], [['42']])
        self.assertEqual(result['messages'], [
            message(u"Can not create Many-To-One records indirectly, import "
                    u"the field separately")])
        self.assertIs(result['ids'], False)

    def test_fail_noids(self):
        result = self.import_(['value'], [['nameisnoexist:3']])
        self.assertEqual(result['messages'], [message(
            u"No matching record found for name 'nameisnoexist:3' "
            u"in field 'unknown'", moreinfo=moreaction(
                res_model='export.integer'))])
        self.assertIs(result['ids'], False)

        result = self.import_(['value/id'], [['noxidhere']])
        self.assertEqual(result['messages'], [message(
            u"No matching record found for external id 'noxidhere' "
            u"in field 'unknown'", moreinfo=moreaction(
                res_model='ir.model.data', domain=[('model','=','export.integer')]))])
        self.assertIs(result['ids'], False)

        result = self.import_(['value/.id'], [['66']])
        self.assertEqual(result['messages'], [message(
            u"No matching record found for database id '66' "
            u"in field 'unknown'", moreinfo=moreaction(
                res_model='ir.model.data', domain=[('model','=','export.integer')]))])
        self.assertIs(result['ids'], False)

    def test_fail_multiple(self):
        result = self.import_(
            ['value', 'value/id'],
            [['somename', 'somexid']])
        self.assertEqual(result['messages'], [message(
            u"Ambiguous specification for field 'unknown', only provide one of "
            u"name, external id or database id")])
        self.assertIs(result['ids'], False)

class test_m2m(ImporterCase):
    model_name = 'export.many2many'

    # apparently, one and only thing which works is a
    # csv_internal_sep-separated list of ids, xids, or names (depending if
    # m2m/.id, m2m/id or m2m[/anythingelse]
    def test_ids(self):
        id1 = self.registry('export.many2many.other').create(
                self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = self.registry('export.many2many.other').create(
                self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = self.registry('export.many2many.other').create(
                self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = self.registry('export.many2many.other').create(
                self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})
        id5 = self.registry('export.many2many.other').create(
                self.cr, openerp.SUPERUSER_ID, {'value': 99, 'str': 'record4'})

        result = self.import_(['value/.id'], [
            ['%d,%d' % (id1, id2)],
            ['%d,%d,%d' % (id1, id3, id4)],
            ['%d,%d,%d' % (id1, id2, id3)],
            ['%d' % id5]
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 4)

        ids = lambda records: [record.id for record in records]

        b = self.browse()
        self.assertEqual(ids(b[0].value), [id1, id2])
        self.assertEqual(values(b[0].value), [3, 44])

        self.assertEqual(ids(b[2].value), [id1, id2, id3])
        self.assertEqual(values(b[2].value), [3, 44, 84])

    def test_noids(self):
        result = self.import_(['value/.id'], [['42']])
        self.assertEqual(result['messages'], [message(
            u"No matching record found for database id '42' in field "
            u"'unknown'", moreinfo=moreaction(
                res_model='ir.model.data', domain=[('model','=','export.many2many.other')]))])
        self.assertIs(result['ids'], False)

    def test_xids(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})
        records = M2O_o.browse(self.cr, openerp.SUPERUSER_ID, [id1, id2, id3, id4])

        result = self.import_(['value/id'], [
            ['%s,%s' % (self.xid(records[0]), self.xid(records[1]))],
            ['%s' % self.xid(records[3])],
            ['%s,%s' % (self.xid(records[2]), self.xid(records[1]))],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 3)

        b = self.browse()
        self.assertEqual(values(b[0].value), [3, 44])
        self.assertEqual(values(b[2].value), [44, 84])
    def test_noxids(self):
        result = self.import_(['value/id'], [['noxidforthat']])
        self.assertEqual(result['messages'], [message(
            u"No matching record found for external id 'noxidforthat' in field"
            u" 'unknown'", moreinfo=moreaction(
                res_model='ir.model.data', domain=[('model','=','export.many2many.other')]))])
        self.assertIs(result['ids'], False)

    def test_names(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})
        records = M2O_o.browse(self.cr, openerp.SUPERUSER_ID, [id1, id2, id3, id4])

        name = lambda record: record.name_get()[0][1]

        result = self.import_(['value'], [
            ['%s,%s' % (name(records[1]), name(records[2]))],
            ['%s,%s,%s' % (name(records[0]), name(records[1]), name(records[2]))],
            ['%s,%s' % (name(records[0]), name(records[3]))],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 3)

        b = self.browse()
        self.assertEqual(values(b[1].value), [3, 44, 84])
        self.assertEqual(values(b[2].value), [3, 9])

    def test_nonames(self):
        result = self.import_(['value'], [['wherethem2mhavenonames']])
        self.assertEqual(result['messages'], [message(
            u"No matching record found for name 'wherethem2mhavenonames' in "
            u"field 'unknown'", moreinfo=moreaction(
                res_model='export.many2many.other'))])
        self.assertIs(result['ids'], False)

    def test_import_to_existing(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})

        xid = 'myxid'
        result = self.import_(['id', 'value/.id'], [[xid, '%d,%d' % (id1, id2)]])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)
        result = self.import_(['id', 'value/.id'], [[xid, '%d,%d' % (id3, id4)]])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        b = self.browse()
        self.assertEqual(len(b), 1)
        # TODO: replacement of existing m2m values is correct?
        self.assertEqual(values(b[0].value), [84, 9])

class test_o2m(ImporterCase):
    model_name = 'export.one2many'

    def test_name_get(self):
        s = u'Java is a DSL for taking large XML files and converting them ' \
            u'to stack traces'
        result = self.import_(
            ['const', 'value'],
            [['5', s]])
        self.assertEqual(result['messages'], [message(
            u"No matching record found for name '%s' in field 'unknown'" % s,
            moreinfo=moreaction(res_model='export.one2many.child'))])
        self.assertIs(result['ids'], False)

    def test_single(self):
        result = self.import_(['const', 'value/value'], [
            ['5', '63']
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        (b,) = self.browse()
        self.assertEqual(b.const, 5)
        self.assertEqual(values(b.value), [63])

    def test_multicore(self):
        result = self.import_(['const', 'value/value'], [
            ['5', '63'],
            ['6', '64'],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 2)

        b1, b2 = self.browse()
        self.assertEqual(b1.const, 5)
        self.assertEqual(values(b1.value), [63])
        self.assertEqual(b2.const, 6)
        self.assertEqual(values(b2.value), [64])

    def test_multisub(self):
        result = self.import_(['const', 'value/value'], [
            ['5', '63'],
            ['', '64'],
            ['', '65'],
            ['', '66'],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        (b,) = self.browse()
        self.assertEqual(values(b.value), [63, 64, 65, 66])

    def test_multi_subfields(self):
        result = self.import_(['value/str', 'const', 'value/value'], [
            ['this', '5', '63'],
            ['is', '', '64'],
            ['the', '', '65'],
            ['rhythm', '', '66'],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        (b,) = self.browse()
        self.assertEqual(values(b.value), [63, 64, 65, 66])
        self.assertEqual(
            values(b.value, 'str'),
            'this is the rhythm'.split())

    def test_link_inline(self):
        """ m2m-style specification for o2ms
        """
        id1 = self.registry('export.one2many.child').create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Bf', 'value': 109
        })
        id2 = self.registry('export.one2many.child').create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Me', 'value': 262
        })

        result = self.import_(['const', 'value/.id'], [
            ['42', '%d,%d' % (id1, id2)]
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        [b] = self.browse()
        self.assertEqual(b.const, 42)
        # automatically forces link between core record and o2ms
        self.assertEqual(values(b.value), [109, 262])
        self.assertEqual(values(b.value, field='parent_id'), [b, b])

    def test_link(self):
        """ O2M relating to an existing record (update) force a LINK_TO as well
        """
        O2M = self.registry('export.one2many.child')
        id1 = O2M.create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Bf', 'value': 109
        })
        id2 = O2M.create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Me', 'value': 262
        })

        result = self.import_(['const', 'value/.id'], [
            ['42', str(id1)],
            ['', str(id2)],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        [b] = self.browse()
        self.assertEqual(b.const, 42)
        # automatically forces link between core record and o2ms
        self.assertEqual(values(b.value), [109, 262])
        self.assertEqual(values(b.value, field='parent_id'), [b, b])

    def test_link_2(self):
        O2M_c = self.registry('export.one2many.child')
        id1 = O2M_c.create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Bf', 'value': 109
        })
        id2 = O2M_c.create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Me', 'value': 262
        })

        result = self.import_(['const', 'value/.id', 'value/value'], [
            ['42', str(id1), '1'],
            ['', str(id2), '2'],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        [b] = self.browse()
        self.assertEqual(b.const, 42)
        self.assertEqual(values(b.value), [1, 2])
        self.assertEqual(values(b.value, field='parent_id'), [b, b])

class test_o2m_multiple(ImporterCase):
    model_name = 'export.one2many.multiple'

    def test_multi_mixed(self):
        result = self.import_(['const', 'child1/value', 'child2/value'], [
            ['5', '11', '21'],
            ['', '12', '22'],
            ['', '13', '23'],
            ['', '14', ''],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        [b] = self.browse()
        self.assertEqual(values(b.child1), [11, 12, 13, 14])
        self.assertEqual(values(b.child2), [21, 22, 23])

    def test_multi(self):
        result = self.import_(['const', 'child1/value', 'child2/value'], [
            ['5', '11', '21'],
            ['', '12', ''],
            ['', '13', ''],
            ['', '14', ''],
            ['', '', '22'],
            ['', '', '23'],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        [b] = self.browse()
        self.assertEqual(values(b.child1), [11, 12, 13, 14])
        self.assertEqual(values(b.child2), [21, 22, 23])

    def test_multi_fullsplit(self):
        result = self.import_(['const', 'child1/value', 'child2/value'], [
            ['5', '11', ''],
            ['', '12', ''],
            ['', '13', ''],
            ['', '14', ''],
            ['', '', '21'],
            ['', '', '22'],
            ['', '', '23'],
        ])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

        [b] = self.browse()
        self.assertEqual(b.const, 5)
        self.assertEqual(values(b.child1), [11, 12, 13, 14])
        self.assertEqual(values(b.child2), [21, 22, 23])

class test_realworld(common.TransactionCase):
    def test_bigfile(self):
        data = json.loads(pkgutil.get_data(self.__module__, 'contacts_big.json'))
        result = self.registry('res.partner').load(
            self.cr, openerp.SUPERUSER_ID,
            ['name', 'mobile', 'email', 'image'],
            data)
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), len(data))

    def test_backlink(self):
        data = json.loads(pkgutil.get_data(self.__module__, 'contacts.json'))
        result = self.registry('res.partner').load(
            self.cr, openerp.SUPERUSER_ID,
            ["name", "type", "street", "city", "country_id", "category_id",
             "supplier", "customer", "is_company", "parent_id"],
            data)
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), len(data))

    def test_recursive_o2m(self):
        """ The content of the o2m field's dict needs to go through conversion
        as it may be composed of convertables or other relational fields
        """
        self.registry('ir.model.data').clear_caches()
        Model = self.registry('export.one2many.recursive')
        result = Model.load(self.cr, openerp.SUPERUSER_ID,
            ['value', 'child/const', 'child/child1/str', 'child/child2/value'],
            [
                ['4', '42', 'foo', '55'],
                ['', '43', 'bar', '56'],
                ['', '', 'baz', ''],
                ['', '55', 'qux', '57'],
                ['5', '99', 'wheee', ''],
                ['', '98', '', '12'],
            ],
        context=None)

        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 2)

        b = Model.browse(self.cr, openerp.SUPERUSER_ID, result['ids'], context=None)
        self.assertEqual((b[0].value, b[1].value), (4, 5))

        self.assertEqual([child.str for child in b[0].child[1].child1],
                         ['bar', 'baz'])
        self.assertFalse(len(b[1].child[1].child1))
        self.assertEqual([child.value for child in b[1].child[1].child2],
                         [12])

class test_date(ImporterCase):
    model_name = 'export.date'

    def test_empty(self):
        self.assertEqual(
            self.import_(['value'], []),
            {'ids': [], 'messages': []})

    def test_basic(self):
        result = self.import_(['value'], [['2012-02-03']])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

    def test_invalid(self):
        result = self.import_(['value'], [['not really a date']])
        self.assertEqual(result['messages'], [
            message(u"'not really a date' does not seem to be a valid date "
                    u"for field 'unknown'",
                    moreinfo=u"Use the format '2012-12-31'")])
        self.assertIs(result['ids'], False)

class test_datetime(ImporterCase):
    model_name = 'export.datetime'

    def test_empty(self):
        self.assertEqual(
            self.import_(['value'], []),
            {'ids': [], 'messages': []})

    def test_basic(self):
        result = self.import_(['value'], [['2012-02-03 11:11:11']])
        self.assertFalse(result['messages'])
        self.assertEqual(len(result['ids']), 1)

    def test_invalid(self):
        result = self.import_(['value'], [['not really a datetime']])
        self.assertEqual(result['messages'], [
            message(u"'not really a datetime' does not seem to be a valid "
                    u"datetime for field 'unknown'",
                    moreinfo=u"Use the format '2012-12-31 23:59:59'")])
        self.assertIs(result['ids'], False)

    def test_checktz1(self):
        """ Imported date should be interpreted as being in the tz provided by
        the context
        """
        # write dummy tz in user (Asia/Hovd UTC+0700), should be superseded by
        # context
        self.registry('res.users').write(
            self.cr, openerp.SUPERUSER_ID, [openerp.SUPERUSER_ID],
            {'tz': 'Asia/Hovd'})

        # UTC+1400
        result = self.import_(
            ['value'], [['2012-02-03 11:11:11']], {'tz': 'Pacific/Kiritimati'})
        self.assertFalse(result['messages'])
        self.assertEqual(
            values(self.read(domain=[('id', 'in', result['ids'])])),
            ['2012-02-02 21:11:11'])

        # UTC-0930
        result = self.import_(
            ['value'], [['2012-02-03 11:11:11']], {'tz': 'Pacific/Marquesas'})
        self.assertFalse(result['messages'])
        self.assertEqual(
            values(self.read(domain=[('id', 'in', result['ids'])])),
            ['2012-02-03 20:41:11'])

    def test_usertz(self):
        """ If the context does not hold a timezone, the importing user's tz
        should be used
        """
        # UTC +1000
        self.registry('res.users').write(
            self.cr, openerp.SUPERUSER_ID, [openerp.SUPERUSER_ID],
            {'tz': 'Asia/Yakutsk'})

        result = self.import_(
            ['value'], [['2012-02-03 11:11:11']])
        self.assertFalse(result['messages'])
        self.assertEqual(
            values(self.read(domain=[('id', 'in', result['ids'])])),
            ['2012-02-03 01:11:11'])

    def test_notz(self):
        """ If there is no tz either in the context or on the user, falls back
        to UTC
        """
        self.registry('res.users').write(
            self.cr, openerp.SUPERUSER_ID, [openerp.SUPERUSER_ID],
            {'tz': False})

        result = self.import_(['value'], [['2012-02-03 11:11:11']])
        self.assertFalse(result['messages'])
        self.assertEqual(
            values(self.read(domain=[('id', 'in', result['ids'])])),
            ['2012-02-03 11:11:11'])

class test_unique(ImporterCase):
    model_name = 'export.unique'

    @mute_logger('openerp.sql_db')
    def test_unique(self):
        result = self.import_(['value'], [
            ['1'],
            ['1'],
            ['2'],
            ['3'],
            ['3'],
        ])
        self.assertFalse(result['ids'])
        self.assertEqual(result['messages'], [
            dict(message=u"The value for the field 'value' already exists. "
                         u"This might be 'unknown' in the current model, "
                         u"or a field of the same name in an o2m.",
                 type='error', rows={'from': 1, 'to': 1},
                 record=1, field='value'),
            dict(message=u"The value for the field 'value' already exists. "
                         u"This might be 'unknown' in the current model, "
                         u"or a field of the same name in an o2m.",
                 type='error', rows={'from': 4, 'to': 4},
                 record=4, field='value'),
        ])
