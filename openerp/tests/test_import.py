# -*- coding: utf-8 -*-
import openerp.modules.registry
import openerp

from . import common, export_models

def ok(n):
    """ Successful import of ``n`` records

    :param int n: number of records which should have been imported
    """
    return n, 0, 0, 0

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
        self.assertItemsEqual([
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
            ]),
            ok(5))
        self.assertItemsEqual([
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
            ]),
            ok(6))
        self.assertItemsEqual(
            [True] * 6,
            values(self.read()))
