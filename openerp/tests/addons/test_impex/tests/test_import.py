# -*- coding: utf-8 -*-
import openerp.modules.registry
import openerp

from openerp.tests import common

def ok(n):
    """ Successful import of ``n`` records

    :param int n: number of records which should have been imported
    """
    return n, 0, 0, 0

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

def setupModule():
    openerp.tools.config['update'] = {'base': 1}

class ImporterCase(common.TransactionCase):
    model_name = False

    def __init__(self, *args, **kwargs):
        super(ImporterCase, self).__init__(*args, **kwargs)
        self.model = None

    def setUp(self):
        super(ImporterCase, self).setUp()
        self.model = self.registry(self.model_name)

    def import_(self, fields, rows, context=None):
        return self.model.import_data(
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
        self.assertRaises(
            Exception, # dammit
            self.import_, ['.id', 'value'], [['42', '36']])
    def test_create_with_xid(self):
        self.assertEqual(
            self.import_(['id', 'value'], [['somexmlid', '42']]),
            ok(1))
        self.assertEqual(
            'somexmlid',
            self.xid(self.browse()[0]))

    def test_update_with_id(self):
        id = self.model.create(self.cr, openerp.SUPERUSER_ID, {'value': 36})
        self.assertEqual(
            36,
            self.model.browse(self.cr, openerp.SUPERUSER_ID, id).value)

        self.assertEqual(
            self.import_(['.id', 'value'], [[str(id), '42']]),
            ok(1))
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
            ok(0))

    def test_exported(self):
        self.assertEqual(
            self.import_(['value'], [
                ['False'],
                ['True'],
            ]),
            ok(2))
        records = self.read()
        self.assertEqual([
            False,
            True,
        ], values(records))

    def test_falses(self):
        self.assertEqual(
            self.import_(['value'], [
                [u'0'],
                [u'off'],
                [u'false'],
                [u'FALSE'],
                [u'OFF'],
                [u''],
            ]),
            ok(6))
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
        self.assertEqual(
            self.import_(['value'], [
                ['no'],
                ['None'],
                ['nil'],
                ['()'],
                ['f'],
                ['#f'],
                # Problem: OpenOffice (and probably excel) output localized booleans
                ['VRAI'],
            ]),
            ok(7))
        self.assertEqual(
            [True] * 7,
            values(self.read()))

class test_integer_field(ImporterCase):
    model_name = 'export.integer'

    def test_none(self):
        self.assertEqual(
            self.import_(['value'], []),
            ok(0))

    def test_empty(self):
        self.assertEqual(
            self.import_(['value'], [['']]),
            ok(1))
        self.assertEqual(
            [False],
            values(self.read()))

    def test_zero(self):
        self.assertEqual(
            self.import_(['value'], [['0']]),
            ok(1))
        self.assertEqual(
            self.import_(['value'], [['-0']]),
            ok(1))
        self.assertEqual([False, False], values(self.read()))

    def test_positives(self):
        self.assertEqual(
            self.import_(['value'], [
                ['1'],
                ['42'],
                [str(2**31-1)],
                ['12345678']
            ]),
            ok(4))
        self.assertEqual([
            1, 42, 2**31-1, 12345678
        ], values(self.read()))

    def test_negatives(self):
        self.assertEqual(
            self.import_(['value'], [
                ['-1'],
                ['-42'],
                [str(-(2**31 - 1))],
                [str(-(2**31))],
                ['-12345678']
            ]),
            ok(5))
        self.assertEqual([
            -1, -42, -(2**31 - 1), -(2**31), -12345678
        ], values(self.read()))

    def test_out_of_range(self):
        self.assertEqual(
            self.import_(['value'], [[str(2**31)]]),
            error(1, "integer out of range\n", value=2**31))
        # auto-rollbacks if error is in process_liness, but not during
        # ir.model.data write. Can differentiate because former ends lines
        # error lines with "!"
        self.cr.rollback()
        self.assertEqual(
            self.import_(['value'], [[str(-2**32)]]),
            error(1, "integer out of range\n", value=-2**32))


    def test_nonsense(self):
        # FIXME: shit error reporting, exceptions half the time, messages the other half
        self.assertRaises(
            ValueError,
            self.import_, ['value'], [['zorglub']])

class test_float_field(ImporterCase):
    model_name = 'export.float'
    def test_none(self):
        self.assertEqual(
            self.import_(['value'], []),
            ok(0))

    def test_empty(self):
        self.assertEqual(
            self.import_(['value'], [['']]),
            ok(1))
        self.assertEqual(
            [False],
            values(self.read()))

    def test_zero(self):
        self.assertEqual(
            self.import_(['value'], [['0']]),
            ok(1))
        self.assertEqual(
            self.import_(['value'], [['-0']]),
            ok(1))
        self.assertEqual([False, False], values(self.read()))

    def test_positives(self):
        self.assertEqual(
            self.import_(['value'], [
                ['1'],
                ['42'],
                [str(2**31-1)],
                ['12345678'],
                [str(2**33)],
                ['0.000001'],
            ]),
            ok(6))
        self.assertEqual([
            1, 42, 2**31-1, 12345678, 2.0**33, .000001
        ], values(self.read()))

    def test_negatives(self):
        self.assertEqual(
            self.import_(['value'], [
                ['-1'],
                ['-42'],
                [str(-2**31 + 1)],
                [str(-2**31)],
                ['-12345678'],
                [str(-2**33)],
                ['-0.000001'],
            ]),
            ok(7))
        self.assertEqual([
            -1, -42, -(2**31 - 1), -(2**31), -12345678, -2.0**33, -.000001
        ], values(self.read()))

    def test_nonsense(self):
        self.assertRaises(
            ValueError,
            self.import_, ['value'], [['foobar']])

class test_string_field(ImporterCase):
    model_name = 'export.string.bounded'

    def test_empty(self):
        self.assertEqual(
            self.import_(['value'], [['']]),
            ok(1))
        self.assertEqual([False], values(self.read()))

    def test_imported(self):
        self.assertEqual(
            self.import_(['value'], [
                [u'foobar'],
                [u'foobarbaz'],
                [u'Með suð í eyrum við spilum endalaust'],
                [u"People 'get' types. They use them all the time. Telling "
                 u"someone he can't pound a nail with a banana doesn't much "
                 u"surprise him."]
            ]),
            ok(4))
        self.assertEqual([
            u"foobar",
            u"foobarbaz",
            u"Með suð í eyrum ",
            u"People 'get' typ",
        ], values(self.read()))

class test_unbound_string_field(ImporterCase):
    model_name = 'export.string'

    def test_imported(self):
        self.assertEqual(
            self.import_(['value'], [
                [u'í dag viðrar vel til loftárása'],
                # ackbar.jpg
                [u"If they ask you about fun, you tell them – fun is a filthy"
                 u" parasite"]
            ]),
            ok(2))
        self.assertEqual([
            u"í dag viðrar vel til loftárása",
            u"If they ask you about fun, you tell them – fun is a filthy parasite"
        ], values(self.read()))

class test_text(ImporterCase):
    model_name = 'export.text'

    def test_empty(self):
        self.assertEqual(
            self.import_(['value'], [['']]),
            ok(1))
        self.assertEqual([False], values(self.read()))

    def test_imported(self):
        s = (u"Breiðskífa er notað um útgefna hljómplötu sem inniheldur "
             u"stúdíóupptökur frá einum flytjanda. Breiðskífur eru oftast "
             u"milli 25-80 mínútur og er lengd þeirra oft miðuð við 33⅓ "
             u"snúninga 12 tommu vínylplötur (sem geta verið allt að 30 mín "
             u"hvor hlið).\n\nBreiðskífur eru stundum tvöfaldar og eru þær þá"
             u" gefnar út á tveimur geisladiskum eða tveimur vínylplötum.")
        self.assertEqual(
            self.import_(['value'], [[s]]),
            ok(1))
        self.assertEqual([s], values(self.read()))

class test_selection(ImporterCase):
    model_name = 'export.selection'
    translations_fr = [
        ("Qux", "toto"),
        ("Bar", "titi"),
        ("Foo", "tete"),
    ]

    def test_imported(self):
        self.assertEqual(
            self.import_(['value'], [
                ['Qux'],
                ['Bar'],
                ['Foo'],
                ['2'],
            ]),
            ok(4))
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

        # FIXME: can't import an exported selection field label if lang != en_US
        # (see test_export.test_selection.test_localized_export)
        self.assertEqual(
            self.import_(['value'], [
                ['toto'],
                ['tete'],
                ['titi'],
            ], context={'lang': 'fr_FR'}),
            ok(3))
        self.assertEqual([3, 1, 2], values(self.read()))
        self.assertEqual(
            self.import_(['value'], [['Foo']], context={'lang': 'fr_FR'}),
            error(1, "Key/value 'Foo' not found in selection field 'value'",
                  value=False))

    def test_invalid(self):
        self.assertEqual(
            self.import_(['value'], [['Baz']]),
            error(1, "Key/value 'Baz' not found in selection field 'value'",
                  # what the fuck?
                  value=False))
        self.cr.rollback()
        self.assertEqual(
            self.import_(['value'], [[42]]),
            error(1, "Key/value '42' not found in selection field 'value'",
                  value=False))

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
        self.assertEqual(
            self.import_(['value'], [
                ['3'],
                ["Grault"],
            ]),
            ok(2))
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
        self.assertEqual(
            self.import_(['value'], [
                ['toto'],
                ['tete'],
            ], context={'lang': 'fr_FR'}),
            error(1, "Key/value 'toto' not found in selection field 'value'",
                  value=False))
        self.assertEqual(
            self.import_(['value'], [['Wheee']], context={'lang': 'fr_FR'}),
            ok(1))

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

        self.assertEqual(
            self.import_(['value'], [
                # import by name_get
                [name1],
                [name1],
                [name2],
            ]),
            ok(3))
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

        self.assertEqual(
            self.import_(['value/id'], [[xid]]),
            ok(1))
        b = self.browse()
        self.assertEqual(42, b[0].value.value)

    def test_by_id(self):
        integer_id = self.registry('export.integer').create(
            self.cr, openerp.SUPERUSER_ID, {'value': 42})
        self.assertEqual(
            self.import_(['value/.id'], [[integer_id]]),
            ok(1))
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

        self.assertEqual(
            self.import_(['value'], [[name2]]),
            ok(1))
        # FIXME: is it really normal import does not care for name_search collisions?
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

        self.assertRaises(
            ValueError, # Because name_search all the things. Fallback schmallback
            self.import_, ['value'], [
                # import by id, without specifying it
                [integer_id1],
                [integer_id2],
                [integer_id1],
            ])

    def test_sub_field(self):
        """ Does not implicitly create the record, does not warn that you can't
        import m2o subfields (at all)...
        """
        self.assertRaises(
            ValueError, # No record found for 42, name_searches the bloody thing
            self.import_, ['value/value'], [['42']])

    def test_fail_noids(self):
        self.assertRaises(
            ValueError,
            self.import_, ['value'], [['nameisnoexist:3']])
        self.cr.rollback()
        self.assertRaises(
            ValueError,
            self.import_, ['value/id'], [['noxidhere']]),
        self.cr.rollback()
        self.assertRaises(
            Exception, # FIXME: Why can't you be a ValueError like everybody else?
            self.import_, ['value/.id'], [[66]])

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

        self.assertEqual(
            self.import_(['value/.id'], [
                ['%d,%d' % (id1, id2)],
                ['%d,%d,%d' % (id1, id3, id4)],
                ['%d,%d,%d' % (id1, id2, id3)],
                ['%d' % id5]
            ]),
            ok(4))
        ids = lambda records: [record.id for record in records]

        b = self.browse()
        self.assertEqual(ids(b[0].value), [id1, id2])
        self.assertEqual(values(b[0].value), [3, 44])

        self.assertEqual(ids(b[2].value), [id1, id2, id3])
        self.assertEqual(values(b[2].value), [3, 44, 84])

    def test_noids(self):
        try:
            self.import_(['value/.id'], [['42']])
            self.fail("Should have raised an exception")
        except Exception, e:
            self.assertIs(type(e), Exception,
                          "test should be fixed on exception subclass")

    def test_xids(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})
        records = M2O_o.browse(self.cr, openerp.SUPERUSER_ID, [id1, id2, id3, id4])

        self.assertEqual(
            self.import_(['value/id'], [
                ['%s,%s' % (self.xid(records[0]), self.xid(records[1]))],
                ['%s' % self.xid(records[3])],
                ['%s,%s' % (self.xid(records[2]), self.xid(records[1]))],
            ]),
            ok(3))

        b = self.browse()
        self.assertEqual(values(b[0].value), [3, 44])
        self.assertEqual(values(b[2].value), [44, 84])
    def test_noxids(self):
        self.assertRaises(
            ValueError,
            self.import_, ['value/id'], [['noxidforthat']])

    def test_names(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})
        records = M2O_o.browse(self.cr, openerp.SUPERUSER_ID, [id1, id2, id3, id4])

        name = lambda record: dict(record.name_get())[record.id]

        self.assertEqual(
            self.import_(['value'], [
                ['%s,%s' % (name(records[1]), name(records[2]))],
                ['%s,%s,%s' % (name(records[0]), name(records[1]), name(records[2]))],
                ['%s,%s' % (name(records[0]), name(records[3]))],
            ]),
            ok(3))

        b = self.browse()
        self.assertEqual(values(b[1].value), [3, 44, 84])
        self.assertEqual(values(b[2].value), [3, 9])

    def test_nonames(self):
        self.assertRaises(
            ValueError,
            self.import_, ['value'], [['wherethem2mhavenonames']])

    def test_import_to_existing(self):
        M2O_o = self.registry('export.many2many.other')
        id1 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 3, 'str': 'record0'})
        id2 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 44, 'str': 'record1'})
        id3 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 84, 'str': 'record2'})
        id4 = M2O_o.create(self.cr, openerp.SUPERUSER_ID, {'value': 9, 'str': 'record3'})

        xid = 'myxid'
        self.assertEqual(
            self.import_(['id', 'value/.id'], [[xid, '%d,%d' % (id1, id2)]]),
            ok(1))
        self.assertEqual(
            self.import_(['id', 'value/.id'], [[xid, '%d,%d' % (id3, id4)]]),
            ok(1))

        b = self.browse()
        self.assertEqual(len(b), 1)
        # TODO: replacement of existing m2m values is correct?
        self.assertEqual(values(b[0].value), [84, 9])

class test_o2m(ImporterCase):
    model_name = 'export.one2many'

    def test_single(self):
        self.assertEqual(
            self.import_(['const', 'value/value'], [
                ['5', '63']
            ]),
            ok(1))

        (b,) = self.browse()
        self.assertEqual(b.const, 5)
        self.assertEqual(values(b.value), [63])

    def test_multicore(self):
        self.assertEqual(
            self.import_(['const', 'value/value'], [
                ['5', '63'],
                ['6', '64'],
            ]),
            ok(2))

        b1, b2 = self.browse()
        self.assertEqual(b1.const, 5)
        self.assertEqual(values(b1.value), [63])
        self.assertEqual(b2.const, 6)
        self.assertEqual(values(b2.value), [64])

    def test_multisub(self):
        self.assertEqual(
            self.import_(['const', 'value/value'], [
                ['5', '63'],
                ['', '64'],
                ['', '65'],
                ['', '66'],
            ]),
            ok(4))

        (b,) = self.browse()
        self.assertEqual(values(b.value), [63, 64, 65, 66])

    def test_multi_subfields(self):
        self.assertEqual(
            self.import_(['value/str', 'const', 'value/value'], [
                ['this', '5', '63'],
                ['is', '', '64'],
                ['the', '', '65'],
                ['rhythm', '', '66'],
            ]),
            ok(4))

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

        self.assertEqual(
            self.import_(['const', 'value/.id'], [
                ['42', str(id1)],
                ['', str(id2)],
            ]),
            ok(2))

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

        self.assertEqual(
            self.import_(['const', 'value/.id', 'value/value'], [
                ['42', str(id1), '1'],
                ['', str(id2), '2'],
            ]),
            ok(2))

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
        self.assertEqual(
            self.import_(['const', 'child1/value', 'child2/value'], [
                ['5', '11', '21'],
                ['', '12', '22'],
                ['', '13', '23'],
                ['', '14', ''],
            ]),
            ok(4))
        # Oh yeah, that's the stuff
        (b, b1, b2) = self.browse()
        self.assertEqual(values(b.child1), [11])
        self.assertEqual(values(b.child2), [21])

        self.assertEqual(values(b1.child1), [12])
        self.assertEqual(values(b1.child2), [22])

        self.assertEqual(values(b2.child1), [13, 14])
        self.assertEqual(values(b2.child2), [23])

    def test_multi(self):
        self.assertEqual(
            self.import_(['const', 'child1/value', 'child2/value'], [
                ['5', '11', '21'],
                ['', '12', ''],
                ['', '13', ''],
                ['', '14', ''],
                ['', '', '22'],
                ['', '', '23'],
            ]),
            ok(6))
        # What the actual fuck?
        (b, b1) = self.browse()
        self.assertEqual(values(b.child1), [11, 12, 13, 14])
        self.assertEqual(values(b.child2), [21])
        self.assertEqual(values(b1.child2), [22, 23])

    def test_multi_fullsplit(self):
        self.assertEqual(
            self.import_(['const', 'child1/value', 'child2/value'], [
                ['5', '11', ''],
                ['', '12', ''],
                ['', '13', ''],
                ['', '14', ''],
                ['', '', '21'],
                ['', '', '22'],
                ['', '', '23'],
            ]),
            ok(7))
        # oh wow
        (b, b1) = self.browse()
        self.assertEqual(b.const, 5)
        self.assertEqual(values(b.child1), [11, 12, 13, 14])
        self.assertEqual(b1.const, 36)
        self.assertEqual(values(b1.child2), [21, 22, 23])

# function, related, reference: written to db as-is...
# => function uses @type for value coercion/conversion
