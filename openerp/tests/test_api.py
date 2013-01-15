
from openerp.tools import mute_logger
from openerp.osv.orm import browse_record
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
