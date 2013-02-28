
from openerp.tools import mute_logger
from openerp.osv.orm import Session, Record, Recordset, Null, except_orm
import common


class TestAPI(common.TransactionCase):
    """ test the new API of the ORM """

    def setUp(self):
        super(TestAPI, self).setUp()
        self.session = Session(self.cr, self.uid, None)
        self.Partner = self.session.model('res.partner')
        self.Users = self.session.model('res.users')

    def assertIsKind(self, value, kind, model):
        """ check for isinstance(value, kind) and value._name == model """
        self.assertIsInstance(value, kind)
        self.assertEqual(value._name, model)

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
            self.assertIsKind(p, Record, 'res.partner')
        self.assertEqual([p.id for p in partners], ids)

        partners2 = self.Partner.search(domain)
        self.assertEqual(partners, partners2)

    @mute_logger('openerp.osv.orm')
    def test_01_query_offset(self):
        """ Build a recordset with offset, and check equivalence. """
        ids = self.Partner.search(self.cr, self.uid, [], offset=10)
        partners = self.Partner.browse(self.cr, self.uid, ids)
        self.assertTrue(partners)

        partners1 = self.Partner.query(self.cr, self.uid, [], offset=10)
        self.assertEqual(list(partners1), list(partners))

        partners2 = self.Partner.query(self.cr, self.uid, [])[10:]
        self.assertIsKind(partners2, Recordset, 'res.partner')
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
        self.assertIsKind(partners2, Recordset, 'res.partner')
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
        self.assertIsKind(partners2, Recordset, 'res.partner')
        self.assertEqual(list(partners2), list(partners))

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
        """ Check that relation fields return records, recordsets or nulls. """
        user = self.Users.browse(self.cr, self.uid, self.uid)
        self.assertIsKind(user, Record, 'res.users')
        # Check for a programming bug: accessing 'partner_id' should read all
        # prefetched fields in the record cache, and many2many fields should not
        # be prefetched.  When rewriting the record access, I observed that
        # many2many fields may be anyway read, and put in the cache as a list of
        # ids instead of a recordset.
        self.assertIsKind(user.partner_id, Record, 'res.partner')
        self.assertIsKind(user.groups_id, Recordset, 'res.groups')

        partners = self.Partner.query(self.cr, self.uid, [])
        for name, cinfo in partners._all_columns.iteritems():
            if cinfo.column._type in ('many2one', 'reference'):
                for p in partners:
                    if p[name]:
                        self.assertIsKind(p[name], Record, cinfo.column._obj)
                    else:
                        self.assertIsKind(p[name], Null, cinfo.column._obj)
            elif cinfo.column._type in ('one2many', 'many2many'):
                for p in partners:
                    self.assertIsKind(p[name], Recordset, cinfo.column._obj)

    @mute_logger('openerp.osv.orm')
    def test_07_null(self):
        """ Check behavior of null instances. """
        # select a partner without a parent
        partner = self.Partner.query(self.cr, self.uid, [('parent_id', '=', False)])[0]

        # check partner and related null instances
        self.assertTrue(partner)
        self.assertIsKind(partner, Record, 'res.partner')

        self.assertFalse(partner.parent_id)
        self.assertIsKind(partner.parent_id, Null, 'res.partner')

        self.assertIs(partner.parent_id.id, False)

        self.assertFalse(partner.parent_id.user_id)
        self.assertIsKind(partner.parent_id.user_id, Null, 'res.users')

        self.assertIs(partner.parent_id.user_id.name, False)

        self.assertFalse(partner.parent_id.user_id.groups_id)
        self.assertIsKind(partner.parent_id.user_id.groups_id, Recordset, 'res.groups')

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
        self.assertFalse(partners.session.context)
        self.assertEqual(partners.session.user.id, self.uid)

        # get the partners company, and check its session data
        partner = partners[0]
        self.assertEqual(partner.session.uid, self.uid)
        company = partner.company_id
        self.assertEqual(company.session.uid, self.uid)

        # check that current user can modify the company
        company.write({'name': 'Fools'})

        # retrieve the demo user
        Users = partners.session.model('res.users')
        demo = Users.query([('login', '=', 'demo')])[0]
        self.assertNotEqual(demo.id, self.uid)

        # remake recordset with demo user, and check session data
        partners = partners.with_session(user=demo)
        self.assertEqual(partners.session.user, demo)
        partner = partners[0]
        self.assertEqual(partner.session.user, demo)
        company = partner.company_id
        self.assertEqual(company.session.user, demo)

        # demo user cannot modify the company
        with self.assertRaises(except_orm):
            company.write({'name': 'Pricks'})

    @mute_logger('openerp.osv.orm')
    def test_50_record_recordset(self):
        """ Check properties record and recordset. """
        ps = self.Partner.query(self.cr, self.uid, [('name', 'ilike', 'a')], limit=1)
        self.assertEqual(ps.recordset, ps)
        p = ps.record
        self.assertEqual(p, ps[0])
        self.assertEqual(p.recordset, ps)

    @mute_logger('openerp.osv.orm')
    def test_60_contains(self):
        """ Test membership on recordset. """
        ps = self.Partner.query(self.cr, self.uid, [('name', 'ilike', 'a')], limit=1)
        p = ps.record
        ps = self.Partner.query(self.cr, self.uid, [('name', 'ilike', 'a')])
        self.assertTrue(p in ps)

    @mute_logger('openerp.osv.orm')
    def test_60_concat(self):
        """ Check concatenation of recordsets. """
        pa = self.Partner.query(self.cr, self.uid, [('name', 'ilike', 'a')])
        pb = self.Partner.query(self.cr, self.uid, [('name', 'ilike', 'b')])
        pab = pa + pb
        self.assertEqual(list(pab), list(pa) + list(pb))
