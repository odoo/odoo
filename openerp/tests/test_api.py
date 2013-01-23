
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
    def test_01_query_offset(self):
        """ Build a recordset with offset, and check equivalence. """
        ids = self.Partner.search(self.cr, self.uid, [], offset=10)
        partners = self.Partner.browse(self.cr, self.uid, ids)
        self.assertTrue(partners)

        partners1 = self.Partner.query(self.cr, self.uid, [], offset=10)
        self.assertEqual(list(partners1), list(partners))

        partners2 = self.Partner.query(self.cr, self.uid, [])[10:]
        self.assertEqual(list(partners2), list(partners))

    @mute_logger('openerp.osv.orm')
    def test_02_query_limit(self):
        """ Build a recordset with offset, and check equivalence. """
        ids = self.Partner.search(self.cr, self.uid, [], limit=10)
        partners = self.Partner.browse(self.cr, self.uid, ids)
        self.assertTrue(partners)

        partners1 = self.Partner.query(self.cr, self.uid, [], limit=10)
        self.assertEqual(list(partners1), list(partners))

        partners2 = self.Partner.query(self.cr, self.uid, [])[:10]
        self.assertEqual(list(partners2), list(partners))

    @mute_logger('openerp.osv.orm')
    def test_03_query_offset_limit(self):
        """ Build a recordset with offset and limit, and check equivalence. """
        ids = self.Partner.search(self.cr, self.uid, [], offset=3, limit=7)
        partners = self.Partner.browse(self.cr, self.uid, ids)
        self.assertTrue(partners)

        partners1 = self.Partner.query(self.cr, self.uid, [], offset=3, limit=7)
        self.assertEqual(list(partners1), list(partners))

        partners2 = self.Partner.query(self.cr, self.uid, [])[3:10]
        self.assertEqual(list(partners2), list(partners))

    @mute_logger('openerp.osv.orm')
    def test_04_query_multi_slicing(self):
        """ Build a recordset with multiple slicings, and check equivalence. """
        ids = self.Partner.search(self.cr, self.uid, [], offset=3, limit=7)
        partners = self.Partner.browse(self.cr, self.uid, ids)
        self.assertTrue(partners)

        partners1 = self.Partner.query(self.cr, self.uid, [])[1:10][2:12]
        self.assertEqual(list(partners1), list(partners))

    @mute_logger('openerp.osv.orm')
    def test_05_immutable(self):
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
    def test_06_fields(self):
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
        """ Call old-style methods in the old-fashioned way. """
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
        """ Call old-style methods in the new API style. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)

        # call method write on partners itself, and check its effect
        partners.write({'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('openerp.osv.orm')
    def test_25_old_new(self):
        """ Call old-style methods on records (new API style). """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)

        # call method write on partner records
        for p in partners:
            p.write({'active': False})

        # re-browse the records to check the method's effect
        for p in partners.browse(map(int, partners)):
            self.assertFalse(p.active)

    @mute_logger('openerp.osv.orm')
    def test_30_new_old(self):
        """ Call new-style methods in the old-fashioned way. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)
        ids = map(int, partners)

        # call method name_get on partners itself, and check its effect
        res = partners.name_get(self.cr, self.uid, ids)
        self.assertEqual(len(res), len(ids))
        self.assertEqual(set(val[0] for val in res), set(ids))

    @mute_logger('openerp.osv.orm')
    def test_40_new_new(self):
        """ Call new-style methods in the new API style. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)

        # call method name_get on partners itself, and check its effect
        res = partners.name_get()
        self.assertEqual(len(res), len(partners))
        self.assertEqual(set(val[0] for val in res), set(map(int, partners)))

    @mute_logger('openerp.osv.orm')
    def test_45_new_new(self):
        """ Call new-style methods on records (new API style). """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)

        # call method name_get on partner records, and check its effect
        for p in partners:
            res = p.name_get()
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0][0], p.id)

    @mute_logger('openerp.osv.orm')
    def test_50_session(self):
        """ Call session methods. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.query(self.cr, self.uid, domain)
        self.assertTrue(partners)

        # check content of partners.session
        self.assertEqual(partners.session.cr, self.cr)
        self.assertEqual(partners.session.uid, self.uid)
        self.assertEqual(partners.session.user.id, self.uid)
        self.assertFalse(partners.session.context)

        # access another model from partners.session
        users_model = partners.session.model('res.users')
        self.assertEqual(users_model.session, partners.session)

        # call query from a session-aware model
        users = users_model.query([])
        self.assertTrue(users.is_recordset())
        self.assertIn(partners.session.user, users)

        # pick another user
        user2 = [u for u in users if u != partners.session.user][0]
        self.assertNotEqual(user2, partners.session.user)

        # make another query as user
        session2 = partners.session.copy(user=user2)
        self.assertNotEqual(session2, partners.session)
        partners2 = session2.model('res.partner').query(domain)
        self.assertTrue(partners2.is_recordset())
        self.assertEqual(partners2.session.user, user2)
