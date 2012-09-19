# -*- coding: utf-8 -*-
import openerp.modules.registry
import openerp

from openerp.tests import common
from openerp.tools.misc import mute_logger

def message(msg, type='error', from_=0, to_=0, record=0, field='value'):
    return {
        'type': type,
        'rows': {'from': from_, 'to': to_},
        'record': record,
        'field': field,
        'message': msg
    }

def error(row, message, record=None, **kwargs):
    """ Failed import of the record ``record`` at line ``row``, with the error
    message ``message``

    :param str message:
    :param dict record:
    """
    return (
        -1, dict(record or {}, **kwargs),
        "Line %d : %s" % (row, message),
        '')

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
            [('model', '=', record._table_name), ('res_id', '=', record.id)])
        if ids:
            d = ModelData.read(
                self.cr, openerp.SUPERUSER_ID, ids, ['name', 'module'])[0]
            if d['module']:
                return '%s.%s' % (d['module'], d['name'])
            return d['name']

        name = dict(record.name_get())[record.id]
        # fix dotted name_get results, otherwise xid lookups blow up
        name = name.replace('.', '-')
        ModelData.create(self.cr, openerp.SUPERUSER_ID, {
            'name': name,
            'model': record._table_name,
            'res_id': record.id,
            'module': '__test__'
        })
        return '__test__.' + name

class test_ids_stuff(ImporterCase):
    model_name = 'export.integer'

    def test_create_with_id(self):
        ids, messages = self.import_(['.id', 'value'], [['42', '36']])
        self.assertIs(ids, False)
        self.assertEqual(messages, [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'field': '.id',
            'message': u"Unknown database identifier '42'",
        }])
    def test_create_with_xid(self):
        ids, messages = self.import_(['id', 'value'], [['somexmlid', '42']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)
        self.assertEqual(
            'somexmlid',
            self.xid(self.browse()[0]))

    def test_update_with_id(self):
        id = self.model.create(self.cr, openerp.SUPERUSER_ID, {'value': 36})
        self.assertEqual(
            36,
            self.model.browse(self.cr, openerp.SUPERUSER_ID, id).value)

        ids, messages = self.import_(['.id', 'value'], [[str(id), '42']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)
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
            ([], []))

    def test_exported(self):
        ids, messages = self.import_(['value'], [['False'], ['True'], ])
        self.assertEqual(len(ids), 2)
        self.assertFalse(messages)
        records = self.read()
        self.assertEqual([
            False,
            True,
        ], values(records))

    def test_falses(self):
        ids, messages = self.import_(
            ['value'],
            [[u'0'], [u'off'],
             [u'false'], [u'FALSE'],
             [u'OFF'], [u''],
        ])
        self.assertEqual(len(ids), 6)
        self.assertFalse(messages)
        self.assertEqual([
                False,
                False,
                False,
                False,
                False,
                False,
            ],
            values(self.read()))

    def test_trues(self):
        ids, messages = self.import_(
            ['value'],
            [['no'],
             ['None'],
             ['nil'],
             ['()'],
             ['f'],
             ['#f'],
             # Problem: OpenOffice (and probably excel) output localized booleans
             ['VRAI'],
        ])
        self.assertEqual(len(ids), 7)
        # FIXME: should warn for values which are not "true", "yes" or "1"
        self.assertFalse(messages)
        self.assertEqual(
            [True] * 7,
            values(self.read()))

class test_integer_field(ImporterCase):
    model_name = 'export.integer'

    def test_none(self):
        self.assertEqual(
            self.import_(['value'], []),
            ([], []))

    def test_empty(self):
        ids, messages = self.import_(['value'], [['']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)
        self.assertEqual(
            [False],
            values(self.read()))

    def test_zero(self):
        ids, messages = self.import_(['value'], [['0']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)

        ids, messages = self.import_(['value'], [['-0']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)

        self.assertEqual([False, False], values(self.read()))

    def test_positives(self):
        ids, messages = self.import_(['value'], [
            ['1'],
            ['42'],
            [str(2**31-1)],
            ['12345678']
        ])
        self.assertEqual(len(ids), 4)
        self.assertFalse(messages)

        self.assertEqual([
            1, 42, 2**31-1, 12345678
        ], values(self.read()))

    def test_negatives(self):
        ids, messages = self.import_(['value'], [
            ['-1'],
            ['-42'],
            [str(-(2**31 - 1))],
            [str(-(2**31))],
            ['-12345678']
        ])
        self.assertEqual(len(ids), 5)
        self.assertFalse(messages)
        self.assertEqual([
            -1, -42, -(2**31 - 1), -(2**31), -12345678
        ], values(self.read()))

    @mute_logger('openerp.sql_db')
    def test_out_of_range(self):
        ids, messages = self.import_(['value'], [[str(2**31)]])
        self.assertIs(ids, False)
        self.assertEqual(messages, [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'message': "integer out of range\n"
        }])

        ids, messages = self.import_(['value'], [[str(-2**32)]])
        self.assertIs(ids, False)
        self.assertEqual(messages, [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'message': "integer out of range\n"
        }])

    def test_nonsense(self):
        ids, messages = self.import_(['value'], [['zorglub']])
        self.assertIs(ids, False)
        self.assertEqual(messages, [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'field': 'value',
            'message': u"invalid literal for int() with base 10: 'zorglub'",
        }])

class test_float_field(ImporterCase):
    model_name = 'export.float'
    def test_none(self):
        self.assertEqual(
            self.import_(['value'], []),
            ([], []))

    def test_empty(self):
        ids, messages = self.import_(['value'], [['']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)
        self.assertEqual(
            [False],
            values(self.read()))

    def test_zero(self):
        ids, messages = self.import_(['value'], [['0']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)

        ids, messages = self.import_(['value'], [['-0']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)

        self.assertEqual([False, False], values(self.read()))

    def test_positives(self):
        ids, messages = self.import_(['value'], [
            ['1'],
            ['42'],
            [str(2**31-1)],
            ['12345678'],
            [str(2**33)],
            ['0.000001'],
        ])
        self.assertEqual(len(ids), 6)
        self.assertFalse(messages)

        self.assertEqual([
            1, 42, 2**31-1, 12345678, 2.0**33, .000001
        ], values(self.read()))

    def test_negatives(self):
        ids, messages = self.import_(['value'], [
            ['-1'],
            ['-42'],
            [str(-2**31 + 1)],
            [str(-2**31)],
            ['-12345678'],
            [str(-2**33)],
            ['-0.000001'],
        ])
        self.assertEqual(len(ids), 7)
        self.assertFalse(messages)
        self.assertEqual([
            -1, -42, -(2**31 - 1), -(2**31), -12345678, -2.0**33, -.000001
        ], values(self.read()))

    def test_nonsense(self):
        ids, messages = self.import_(['value'], [['foobar']])
        self.assertIs(ids, False)
        self.assertEqual(messages, [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'field': 'value',
            'message': u"invalid literal for float(): foobar",
        }])

class test_string_field(ImporterCase):
    model_name = 'export.string.bounded'

    def test_empty(self):
        ids, messages = self.import_(['value'], [['']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)
        self.assertEqual([False], values(self.read()))

    def test_imported(self):
        ids, messages = self.import_(['value'], [
            [u'foobar'],
            [u'foobarbaz'],
            [u'Með suð í eyrum við spilum endalaust'],
            [u"People 'get' types. They use them all the time. Telling "
             u"someone he can't pound a nail with a banana doesn't much "
             u"surprise him."]
        ])
        self.assertEqual(len(ids), 4)
        self.assertFalse(messages)
        self.assertEqual([
            u"foobar",
            u"foobarbaz",
            u"Með suð í eyrum ",
            u"People 'get' typ",
        ], values(self.read()))

class test_unbound_string_field(ImporterCase):
    model_name = 'export.string'

    def test_imported(self):
        ids, messages = self.import_(['value'], [
            [u'í dag viðrar vel til loftárása'],
            # ackbar.jpg
            [u"If they ask you about fun, you tell them – fun is a filthy"
             u" parasite"]
        ])
        self.assertEqual(len(ids), 2)
        self.assertFalse(messages)
        self.assertEqual([
            u"í dag viðrar vel til loftárása",
            u"If they ask you about fun, you tell them – fun is a filthy parasite"
        ], values(self.read()))

class test_text(ImporterCase):
    model_name = 'export.text'

    def test_empty(self):
        ids, messages = self.import_(['value'], [['']])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)
        self.assertEqual([False], values(self.read()))

    def test_imported(self):
        s = (u"Breiðskífa er notað um útgefna hljómplötu sem inniheldur "
             u"stúdíóupptökur frá einum flytjanda. Breiðskífur eru oftast "
             u"milli 25-80 mínútur og er lengd þeirra oft miðuð við 33⅓ "
             u"snúninga 12 tommu vínylplötur (sem geta verið allt að 30 mín "
             u"hvor hlið).\n\nBreiðskífur eru stundum tvöfaldar og eru þær þá"
             u" gefnar út á tveimur geisladiskum eða tveimur vínylplötum.")
        ids, messages = self.import_(['value'], [[s]])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)
        self.assertEqual([s], values(self.read()))

class test_selection(ImporterCase):
    model_name = 'export.selection'
    translations_fr = [
        ("Qux", "toto"),
        ("Bar", "titi"),
        ("Foo", "tete"),
    ]

    def test_imported(self):
        ids, messages = self.import_(['value'], [
            ['Qux'],
            ['Bar'],
            ['Foo'],
            ['2'],
        ])
        self.assertEqual(len(ids), 4)
        self.assertFalse(messages)
        self.assertEqual([3, 2, 1, 2], values(self.read()))

    def test_imported_translated(self):
        self.registry('res.lang').create(self.cr, openerp.SUPERUSER_ID, {
            'name': u'Français',
            'code': 'fr_FR',
            'translatable': True,
            'date_format': '%d.%m.%Y',
            'decimal_point': ',',
            'thousand_sep': ' ',
        })
        Translations = self.registry('ir.translation')
        for source, value in self.translations_fr:
            Translations.create(self.cr, openerp.SUPERUSER_ID, {
                'name': 'export.selection,value',
                'lang': 'fr_FR',
                'type': 'selection',
                'src': source,
                'value': value
            })

        ids, messages = self.import_(['value'], [
            ['toto'],
            ['tete'],
            ['titi'],
        ], context={'lang': 'fr_FR'})
        self.assertEqual(len(ids), 3)
        self.assertFalse(messages)

        self.assertEqual([3, 1, 2], values(self.read()))

        ids, messages = self.import_(['value'], [['Foo']], context={'lang': 'fr_FR'})
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)

    def test_invalid(self):
        ids, messages = self.import_(['value'], [['Baz']])
        self.assertIs(ids, False)
        self.assertEqual(messages, [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'field': 'value',
            'message': "Value 'Baz' not found in selection field 'value'",
        }])

        ids, messages = self.import_(['value'], [[42]])
        self.assertIs(ids, False)
        self.assertEqual(messages, [{
            'type': 'error',
            'rows': {'from': 0, 'to': 0},
            'record': 0,
            'field': 'value',
            'message': "Value '42' not found in selection field 'value'",
        }])

class test_selection_function(ImporterCase):
    model_name = 'export.selection.function'
    translations_fr = [
        ("Corge", "toto"),
        ("Grault", "titi"),
        ("Whee", "tete"),
        ("Moog", "tutu"),
    ]

    def test_imported(self):
        """ import uses fields_get, so translates import label (may or may not
        be good news) *and* serializes the selection function to reverse it:
        import does not actually know that the selection field uses a function
        """
        # NOTE: conflict between a value and a label => ?
        ids, messages = self.import_(['value'], [
            ['3'],
            ["Grault"],
        ])
        self.assertEqual(len(ids), 2)
        self.assertFalse(messages)
        self.assertEqual(
            ['3', '1'],
            values(self.read()))

    def test_translated(self):
        """ Expects output of selection function returns translated labels
        """
        self.registry('res.lang').create(self.cr, openerp.SUPERUSER_ID, {
            'name': u'Français',
            'code': 'fr_FR',
            'translatable': True,
            'date_format': '%d.%m.%Y',
            'decimal_point': ',',
            'thousand_sep': ' ',
        })
        Translations = self.registry('ir.translation')
        for source, value in self.translations_fr:
            Translations.create(self.cr, openerp.SUPERUSER_ID, {
                'name': 'export.selection,value',
                'lang': 'fr_FR',
                'type': 'selection',
                'src': source,
                'value': value
            })
        ids, messages = self.import_(['value'], [
            ['toto'],
            ['tete'],
        ], context={'lang': 'fr_FR'})
        self.assertIs(ids, False)
        self.assertEqual(messages, [{
            'type': 'error',
            'rows': {'from': 1, 'to': 1},
            'record': 1,
            'field': 'value',
            'message': "Value 'tete' not found in selection field 'value'",
        }])
        ids, messages = self.import_(['value'], [['Wheee']], context={'lang': 'fr_FR'})
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)

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

        ids , messages = self.import_(['value'], [
            # import by name_get
            [name1],
            [name1],
            [name2],
        ])
        self.assertFalse(messages)
        self.assertEqual(len(ids), 3)
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

        ids, messages = self.import_(['value/id'], [[xid]])
        self.assertFalse(messages)
        self.assertEqual(len(ids), 1)
        b = self.browse()
        self.assertEqual(42, b[0].value.value)

    def test_by_id(self):
        integer_id = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        ids, messages = self.import_(['value/.id'], [[integer_id]])
        self.assertFalse(messages)
        self.assertEqual(len(ids), 1)
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

        ids, messages = self.import_(['value'], [[name2]])
        self.assertEqual(
            messages,
            [message(u"Found multiple matches for field 'value' (2 matches)",
                     type='warning')])
        self.assertEqual(len(ids), 1)
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
        ids, messages = self.import_(['value'], [
                # import by id, without specifying it
                [integer_id1],
                [integer_id2],
                [integer_id1],
        ])
        self.assertEqual(messages, [
            message(u"No matching record found for name '%s' in field 'value'" % id,
                    from_=index, to_=index, record=index)
            for index, id in enumerate([integer_id1, integer_id2, integer_id1])])
        self.assertIs(ids, False)

    def test_sub_field(self):
        """ Does not implicitly create the record, does not warn that you can't
        import m2o subfields (at all)...
        """
        ids, messages = self.import_(['value/value'], [['42']])
        self.assertEqual(messages, [
            message(u"Can not create Many-To-One records indirectly, import "
                    u"the field separately")])
        self.assertIs(ids, False)

    def test_fail_noids(self):
        ids, messages = self.import_(['value'], [['nameisnoexist:3']])
        self.assertEqual(messages, [message(
            u"No matching record found for name 'nameisnoexist:3' "
            u"in field 'value'")])
        self.assertIs(ids, False)

        ids, messages = self.import_(['value/id'], [['noxidhere']])
        self.assertEqual(messages, [message(
            u"No matching record found for external id 'noxidhere' "
            u"in field 'value'")])
        self.assertIs(ids, False)

        ids, messages = self.import_(['value/.id'], [['66']])
        self.assertEqual(messages, [message(
            u"No matching record found for database id '66' "
            u"in field 'value'")])
        self.assertIs(ids, False)

    def test_fail_multiple(self):
        ids, messages = self.import_(
            ['value', 'value/id'],
            [['somename', 'somexid']])
        self.assertEqual(messages, [message(
            u"Ambiguous specification for field 'value', only provide one of "
            u"name, external id or database id")])
        self.assertIs(ids, False)

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

        ids, messages = self.import_(['value/.id'], [
            ['%d,%d' % (id1, id2)],
            ['%d,%d,%d' % (id1, id3, id4)],
            ['%d,%d,%d' % (id1, id2, id3)],
            ['%d' % id5]
        ])
        self.assertFalse(messages)
        self.assertEqual(len(ids), 4)

        ids = lambda records: [record.id for record in records]

        b = self.browse()
        self.assertEqual(ids(b[0].value), [id1, id2])
        self.assertEqual(values(b[0].value), [3, 44])

        self.assertEqual(ids(b[2].value), [id1, id2, id3])
        self.assertEqual(values(b[2].value), [3, 44, 84])

    def test_noids(self):
        ids, messages = self.import_(['value/.id'], [['42']])
        self.assertEqual(messages, [message(
            u"No matching record found for database id '42' in field "
            u"'value'")])
        self.assertIs(ids, False)

    def test_xids(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})
        records = M2O_o.browse(self.cr, openerp.SUPERUSER_ID, [id1, id2, id3, id4])

        ids, messages = self.import_(['value/id'], [
            ['%s,%s' % (self.xid(records[0]), self.xid(records[1]))],
            ['%s' % self.xid(records[3])],
            ['%s,%s' % (self.xid(records[2]), self.xid(records[1]))],
        ])
        self.assertFalse(messages)
        self.assertEqual(len(ids), 3)

        b = self.browse()
        self.assertEqual(values(b[0].value), [3, 44])
        self.assertEqual(values(b[2].value), [44, 84])
    def test_noxids(self):
        ids, messages = self.import_(['value/id'], [['noxidforthat']])
        self.assertEqual(messages, [message(
            u"No matching record found for external id 'noxidforthat' "
            u"in field 'value'")])
        self.assertIs(ids, False)

    def test_names(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})
        records = M2O_o.browse(self.cr, openerp.SUPERUSER_ID, [id1, id2, id3, id4])

        name = lambda record: dict(record.name_get())[record.id]

        ids, messages = self.import_(['value'], [
            ['%s,%s' % (name(records[1]), name(records[2]))],
            ['%s,%s,%s' % (name(records[0]), name(records[1]), name(records[2]))],
            ['%s,%s' % (name(records[0]), name(records[3]))],
        ])
        self.assertFalse(messages)
        self.assertEqual(len(ids), 3)

        b = self.browse()
        self.assertEqual(values(b[1].value), [3, 44, 84])
        self.assertEqual(values(b[2].value), [3, 9])

    def test_nonames(self):
        ids, messages = self.import_(['value'], [['wherethem2mhavenonames']])
        self.assertEqual(messages, [message(
            u"No matching record found for name 'wherethem2mhavenonames' in "
            u"field 'value'")])
        self.assertIs(ids, False)

    def test_import_to_existing(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})

        xid = 'myxid'
        ids, messages = self.import_(['id', 'value/.id'], [[xid, '%d,%d' % (id1, id2)]])
        self.assertFalse(messages)
        self.assertEqual(len(ids), 1)
        ids, messages = self.import_(['id', 'value/.id'], [[xid, '%d,%d' % (id3, id4)]])
        self.assertFalse(messages)
        self.assertEqual(len(ids), 1)

        b = self.browse()
        self.assertEqual(len(b), 1)
        # TODO: replacement of existing m2m values is correct?
        self.assertEqual(values(b[0].value), [84, 9])

class test_o2m(ImporterCase):
    model_name = 'export.one2many'

    def test_name_get(self):
        # FIXME: bloody hell why can't this just name_create the record?
        self.assertRaises(
            IndexError,
            self.import_,
            ['const', 'value'],
            [['5', u'Java is a DSL for taking large XML files'
                   u' and converting them to stack traces']])

    def test_single(self):
        ids, messages = self.import_(['const', 'value/value'], [
            ['5', '63']
        ])
        self.assertEqual(len(ids), 1)
        self.assertFalse(messages)

        (b,) = self.browse()
        self.assertEqual(b.const, 5)
        self.assertEqual(values(b.value), [63])

    def test_multicore(self):
        ids, messages = self.import_(['const', 'value/value'], [
            ['5', '63'],
            ['6', '64'],
        ])
        self.assertEqual(len(ids), 2)
        self.assertFalse(messages)

        b1, b2 = self.browse()
        self.assertEqual(b1.const, 5)
        self.assertEqual(values(b1.value), [63])
        self.assertEqual(b2.const, 6)
        self.assertEqual(values(b2.value), [64])

    def test_multisub(self):
        ids, messages = self.import_(['const', 'value/value'], [
            ['5', '63'],
            ['', '64'],
            ['', '65'],
            ['', '66'],
        ])
        self.assertEqual(len(ids), 4)
        self.assertFalse(messages)

        (b,) = self.browse()
        self.assertEqual(values(b.value), [63, 64, 65, 66])

    def test_multi_subfields(self):
        ids, messages = self.import_(['value/str', 'const', 'value/value'], [
            ['this', '5', '63'],
            ['is', '', '64'],
            ['the', '', '65'],
            ['rhythm', '', '66'],
        ])
        self.assertEqual(len(ids), 4)
        self.assertFalse(messages)

        (b,) = self.browse()
        self.assertEqual(values(b.value), [63, 64, 65, 66])
        self.assertEqual(
            values(b.value, 'str'),
            'this is the rhythm'.split())

    def test_link_inline(self):
        id1 = self.registry('export.one2many.child').create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Bf', 'value': 109
        })
        id2 = self.registry('export.one2many.child').create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Me', 'value': 262
        })

        try:
            self.import_(['const', 'value/.id'], [
                ['42', '%d,%d' % (id1, id2)]
            ])
            self.fail("Should have raised a valueerror")
        except ValueError, e:
            # should be Exception(Database ID doesn't exist: export.one2many.child : $id1,$id2)
            self.assertIs(type(e), ValueError)
            self.assertEqual(
                e.args[0],
                "invalid literal for int() with base 10: '%d,%d'" % (id1, id2))

    def test_link(self):
        id1 = self.registry('export.one2many.child').create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Bf', 'value': 109
        })
        id2 = self.registry('export.one2many.child').create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Me', 'value': 262
        })

        ids, messages = self.import_(['const', 'value/.id'], [
            ['42', str(id1)],
            ['', str(id2)],
        ])
        self.assertEqual(len(ids), 2)
        self.assertFalse(messages)

        # No record values alongside id => o2m resolution skipped altogether,
        # creates 2 records => remove/don't import columns sideshow columns,
        # get completely different semantics
        b, b1 = self.browse()
        self.assertEqual(b.const, 42)
        self.assertEqual(values(b.value), [])
        self.assertEqual(b1.const, 4)
        self.assertEqual(values(b1.value), [])

    def test_link_2(self):
        O2M_c = self.registry('export.one2many.child')
        id1 = O2M_c.create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Bf', 'value': 109
        })
        id2 = O2M_c.create(self.cr, openerp.SUPERUSER_ID, {
            'str': 'Me', 'value': 262
        })

        ids, messages = self.import_(['const', 'value/.id', 'value/value'], [
            ['42', str(id1), '1'],
            ['', str(id2), '2'],
        ])
        self.assertEqual(len(ids), 2)
        self.assertFalse(messages)

        (b,) = self.browse()
        # if an id (db or xid) is provided, expectations that objects are
        # *already* linked and emits UPDATE (1, id, {}).
        # Noid => CREATE (0, ?, {})
        # TODO: xid ignored aside from getting corresponding db id?
        self.assertEqual(b.const, 42)
        self.assertEqual(values(b.value), [])

        # FIXME: updates somebody else's records?
        self.assertEqual(
            O2M_c.read(self.cr, openerp.SUPERUSER_ID, id1),
            {'id': id1, 'str': 'Bf', 'value': 1, 'parent_id': False})
        self.assertEqual(
            O2M_c.read(self.cr, openerp.SUPERUSER_ID, id2),
            {'id': id2, 'str': 'Me', 'value': 2, 'parent_id': False})

class test_o2m_multiple(ImporterCase):
    model_name = 'export.one2many.multiple'

    def test_multi_mixed(self):
        ids, messages = self.import_(['const', 'child1/value', 'child2/value'], [
            ['5', '11', '21'],
            ['', '12', '22'],
            ['', '13', '23'],
            ['', '14', ''],
        ])
        self.assertEqual(len(ids), 4)
        self.assertFalse(messages)
        # Oh yeah, that's the stuff
        (b, b1, b2) = self.browse()
        self.assertEqual(values(b.child1), [11])
        self.assertEqual(values(b.child2), [21])

        self.assertEqual(values(b1.child1), [12])
        self.assertEqual(values(b1.child2), [22])

        self.assertEqual(values(b2.child1), [13, 14])
        self.assertEqual(values(b2.child2), [23])

    def test_multi(self):
        ids, messages = self.import_(['const', 'child1/value', 'child2/value'], [
            ['5', '11', '21'],
            ['', '12', ''],
            ['', '13', ''],
            ['', '14', ''],
            ['', '', '22'],
            ['', '', '23'],
        ])
        self.assertEqual(len(ids), 6)
        self.assertFalse(messages)
        # What the actual fuck?
        (b, b1) = self.browse()
        self.assertEqual(values(b.child1), [11, 12, 13, 14])
        self.assertEqual(values(b.child2), [21])
        self.assertEqual(values(b1.child2), [22, 23])

    def test_multi_fullsplit(self):
        ids, messages = self.import_(['const', 'child1/value', 'child2/value'], [
            ['5', '11', ''],
            ['', '12', ''],
            ['', '13', ''],
            ['', '14', ''],
            ['', '', '21'],
            ['', '', '22'],
            ['', '', '23'],
        ])
        self.assertEqual(len(ids), 7)
        self.assertFalse(messages)
        # oh wow
        (b, b1) = self.browse()
        self.assertEqual(b.const, 5)
        self.assertEqual(values(b.child1), [11, 12, 13, 14])
        self.assertEqual(b1.const, 36)
        self.assertEqual(values(b1.child2), [21, 22, 23])

# function, related, reference: written to db as-is...
# => function uses @type for value coercion/conversion
