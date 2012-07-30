# -*- coding: utf-8 -*-
import openerp.modules.registry
import openerp

from . import common, export_models

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

def values(seq):
    return [item['value'] for item in seq]

def setupModule():
    openerp.tools.config['update'] = {'base': 1}
    openerp.modules.registry.RegistryManager.new(
        common.DB, update_module=True)

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
        # dafuq? why does that one raise an error?
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

    def test_imported(self):
        self.assertEqual(
            self.import_(['value'], [
                ['Qux'],
                ['Bar'],
                ['Foo'],
                [2],
            ]),
            ok(4))
        self.assertEqual([3, 2, 1, 2], values(self.read()))

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

    def test_imported(self):
        """ By what bloody magic does that thing work?

        => import uses fields_get, so translates import label (may or may not
           be good news) *and* serializes the selection function to reverse
           it: import does not actually know that the selection field uses a
           function
        """
        # TODO: localized import
        self.assertEqual(
            self.import_(['value'], [
                [3],
                ["Grault"],
            ]),
            ok(2))
        self.assertEqual(
            ['3', '1'],
            values(self.read()))
