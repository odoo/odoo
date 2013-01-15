
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
    def test_query(self):
        """ Build a recordset, and check its contents. """
        domain = [('name', 'ilike', 'd')]
        ids = self.Partner.search(self.cr, self.uid, domain)
        partners = self.Partner.query(self.cr, self.uid, domain)

        # partners is a collection of browse records corresponding to ids
        self.assertTrue(ids)
        self.assertTrue(all(isinstance(p, browse_record) for p in partners))
        self.assertEqual([p.id for p in partners], ids)
