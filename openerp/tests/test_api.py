
from openerp.tools import mute_logger
from openerp.osv.orm import Record, BaseModel
import common


class TestAPI(common.TransactionCase):
    """ test the new API of the ORM """

    def setUp(self):
        super(TestAPI, self).setUp()
        self.Partner = self.registry('res.partner')
        self.Users = self.registry('res.users')

    @mute_logger('openerp.osv.orm')
    def test_00_query(self):
        """ Build a recordset, and check its contents. """
        domain = [('name', 'ilike', 'j')]
        ids = self.Partner.search(self.cr, self.uid, domain)
        partners = self.Partner.query(self.cr, self.uid, domain)

        # partners is a collection of browse records corresponding to ids
        self.assertTrue(ids)
        self.assertTrue(partners)
        for p in partners:
            self.assertIsInstance(p, Record)
        self.assertEqual([p.id for p in partners], ids)

    @mute_logger('openerp.osv.orm')
    def test_01_immutable(self):
        """ Check that a recordset remains the same, even after updates. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)
        ids = map(int, partners)

        # modify those partners, and check that partners has not changed
        self.Partner.write(self.cr, self.uid, ids, {'active': False})
        self.assertEqual(ids, map(int, partners))

        # redo the query, and check that the result is now empty
        partners2 = self.Partner.query(self.cr, self.uid, domain)
        self.assertFalse(partners2)

    @mute_logger('openerp.osv.orm')
    def test_02_fields(self):
        """ Check that relation fields return records or recordsets. """
        partners = self.Partner.query(self.cr, self.uid, [])
        for name, cinfo in partners._all_columns.iteritems():
            if cinfo.column._type in ('many2one', 'reference'):
                for p in partners:
                    if p[name]:
                        self.assertIsInstance(p[name], Record)
            elif cinfo.column._type in ('one2many', 'many2many'):
                for p in partners:
                    self.assertIsInstance(p[name], BaseModel)

    @mute_logger('openerp.osv.orm')
    def test_10_old_old(self):
        """ Call old-fashioned methods in the old-fashioned way. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)
        ids = map(int, partners)

        # call method write on partners itself, and check its effect
        partners.write(self.cr, self.uid, ids, {'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('openerp.osv.orm')
    def test_20_old_new(self):
        """ Call old-fashioned methods in the new API style. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)

        # call method write on partners itself, and check its effect
        partners.write({'active': False})
        for p in partners:
            self.assertFalse(p.active)
