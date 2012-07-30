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
        "Line %d : %s\n" % (row, message),
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
            error(1, "integer out of range", value=2**31))
        # auto-rollbacks if error is in process_liness, but not during
        # ir.model.data write. Can differentiate because former ends lines
        # error lines with "!"
        self.cr.rollback()
        self.assertEqual(
            self.import_(['value'], [[str(-2**32)]]),
            error(1, "integer out of range", value=-2**32))


    def test_nonsense(self):
        # dafuq? why does that one raise an error?
        self.assertRaises(
            ValueError,
            self.import_, ['value'], [['zorglub']])
