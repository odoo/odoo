
from openerp.tools import mute_logger
from openerp.osv.orm import browse_record, Model
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
        self.assertTrue(all(isinstance(p, browse_record) for p in partners))
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
    def test_10_old_old(self):
        """ Call old-fashioned methods on recordsets. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)
        ids = map(int, partners)

        # call method write on partners itself, and check its effect
        partners.write(self.cr, self.uid, ids, {'active': False})
        for p in partners:
            self.assertFalse(p.active)
