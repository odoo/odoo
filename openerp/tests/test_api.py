
from openerp import SUPERUSER_ID
from openerp.tools import mute_logger
from openerp.osv.api import scope
from openerp.osv.orm import Record, Recordset, Null, except_orm
import common


class TestAPI(common.TransactionCase):
    """ test the new API of the ORM """

    def setUp(self):
        super(TestAPI, self).setUp()
        self.Partner = self.registry('res.partner')
        self.Users = self.registry('res.users')

    def assertIsKind(self, value, kind, model):
        """ check for isinstance(value, kind) and value._name == model """
        self.assertIsInstance(value, kind)
        self.assertEqual(value._name, model)

    @mute_logger('openerp.osv.orm')
    def test_00_query(self):
        """ Build a recordset, and check its contents. """
        domain = [('name', 'ilike', 'j')]
        ids = self.Partner.search(self.cr, self.uid, domain)
        partners = self.Partner.search(domain)

        # partners is a collection of browse records corresponding to ids
        self.assertTrue(ids)
        self.assertTrue(partners)

        # partners and its contents are instance of the model, and share its ormcache
        self.assertIsKind(partners, Recordset, 'res.partner')
        self.assertIs(partners._ormcache, self.Partner._ormcache)
        for p in partners:
            self.assertIsKind(p, Record, 'res.partner')
            self.assertIs(p._ormcache, self.Partner._ormcache)

        self.assertEqual([p.id for p in partners], ids)
        self.assertEqual(self.Partner.browse(ids), partners)

    @mute_logger('openerp.osv.orm')
    def test_01_query_offset(self):
        """ Build a recordset with offset, and check equivalence. """
        partners1 = self.Partner.search([], offset=10)
        partners2 = self.Partner.search([])[10:]
        self.assertIsKind(partners1, Recordset, 'res.partner')
        self.assertIsKind(partners2, Recordset, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('openerp.osv.orm')
    def test_02_query_limit(self):
        """ Build a recordset with offset, and check equivalence. """
        partners1 = self.Partner.search([], limit=10)
        partners2 = self.Partner.search([])[:10]
        self.assertIsKind(partners1, Recordset, 'res.partner')
        self.assertIsKind(partners2, Recordset, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('openerp.osv.orm')
    def test_03_query_offset_limit(self):
        """ Build a recordset with offset and limit, and check equivalence. """
        partners1 = self.Partner.search([], offset=3, limit=7)
        partners2 = self.Partner.search([])[3:10]
        self.assertIsKind(partners1, Recordset, 'res.partner')
        self.assertIsKind(partners2, Recordset, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('openerp.osv.orm')
    def test_05_immutable(self):
        """ Check that a recordset remains the same, even after updates. """
        domain = [('name', 'ilike', 'j')]
        partners = self.Partner.search(domain)
        self.assertTrue(partners)
        ids = map(int, partners)

        # modify those partners, and check that partners has not changed
        self.Partner.write(self.cr, self.uid, ids, {'active': False})
        self.assertEqual(ids, map(int, partners))

        # redo the search, and check that the result is now empty
        partners2 = self.Partner.search(domain)
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

        partners = self.Partner.search([])
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
        partner = self.Partner.search([('parent_id', '=', False)])[0]

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
        partners = self.Partner.search([('name', 'ilike', 'j')])
        self.assertTrue(partners)
        ids = map(int, partners)

        # call method name_get on partners itself, and check its effect
        res = partners.name_get(self.cr, self.uid, ids)
        self.assertEqual(len(res), len(ids))
        self.assertEqual(set(val[0] for val in res), set(ids))

    @mute_logger('openerp.osv.orm')
    def test_20_old_new(self):
        """ Call old-style methods in the new API style. """
        partners = self.Partner.search([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # call method name_get on partners itself, and check its effect
        res = partners.name_get()
        self.assertEqual(len(res), len(partners))
        self.assertEqual(set(val[0] for val in res), set(map(int, partners)))

    @mute_logger('openerp.osv.orm')
    def test_25_old_new(self):
        """ Call old-style methods on records (new API style). """
        partners = self.Partner.search([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # call method name_get on partner records, and check its effect
        for p in partners:
            res = p.name_get()
            self.assertIsInstance(res, tuple)
            self.assertEqual(res[0], p.id)

    @mute_logger('openerp.osv.orm')
    def test_30_new_old(self):
        """ Call new-style methods in the old-fashioned way. """
        partners = self.Partner.search([('name', 'ilike', 'j')])
        self.assertTrue(partners)
        ids = map(int, partners)

        # call method write on partners itself, and check its effect
        partners.write(self.cr, self.uid, ids, {'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('openerp.osv.orm')
    def test_40_new_new(self):
        """ Call new-style methods in the new API style. """
        partners = self.Partner.search([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # call method write on partners itself, and check its effect
        partners.write({'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('openerp.osv.orm')
    def test_45_new_new(self):
        """ Call new-style methods on records (new API style). """
        partners = self.Partner.search([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # call method write on partner records, and check its effects
        for p in partners:
            p.write({'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('openerp.osv.orm')
    def test_50_scope(self):
        """ Test scope nesting. """
        # retrieve another user
        user = self.Users.search([('id', '!=', self.uid)])[0]
        self.assertNotEqual(user.id, self.uid)

        scope0 = scope.current
        self.assertEqual(scope.cr, self.cr)
        self.assertEqual(scope.uid, self.uid)

        with scope(self.cr, self.uid, {}) as scope1:
            self.assertEqual(scope.current, scope1)
            self.assertEqual(scope.cr, self.cr)
            self.assertEqual(scope.uid, self.uid)

            with self.assertRaises(Exception):
                with scope(user, lang=user.lang) as scope2:
                    self.assertNotEqual(scope.current, scope1)
                    self.assertEqual(scope.cr, self.cr)
                    self.assertEqual(scope.user, user)
                    self.assertEqual(scope.context, {'lang': user.lang})

                    with scope.SUDO():
                        self.assertEqual(scope.uid, SUPERUSER_ID)

                    self.assertEqual(scope.current, scope2)
                    self.assertEqual(scope.user, user)

                    # root scope should be with self.uid
                    self.assertEqual(scope.root.uid, self.uid)

                    with scope.SUDO():
                        self.assertEqual(scope.uid, SUPERUSER_ID)
                        raise Exception()       # exit scope with an exception

                    self.fail("Unreachable statement")

            self.assertEqual(scope.current, scope1)

        self.assertEqual(scope.current, scope0)

    @mute_logger('openerp.osv.orm')
    @mute_logger('openerp.addons.base.ir.ir_model')
    def test_55_scope(self):
        """ Test scope on records. """
        outer_scope = scope.current

        # partners and reachable records are attached to the outer scope
        partners = self.Partner.search([('name', 'ilike', 'j')])
        for x in (partners, partners[0], partners[0].company_id):
            self.assertEqual(x.scope, outer_scope)
        for p in partners:
            self.assertEqual(p.scope, outer_scope)

        # check that current user can read and modify company data
        partners[0].company_id.name
        partners[0].company_id.write({'name': 'Fools'})

        # create a scope with the demo user
        demo = self.Users.search([('login', '=', 'demo')])[0]

        with scope(demo) as inner_scope:
            self.assertNotEqual(inner_scope, outer_scope)

            # partners and related records are still attached to outer_scope
            for x in (partners, partners[0], partners[0].company_id):
                self.assertEqual(x.scope, outer_scope)
            for p in partners:
                self.assertEqual(p.scope, outer_scope)

            # create record instances attached to the inner scope
            demo_partners = partners.browse(map(int, partners))
            for x in (demo_partners, demo_partners[0], demo_partners[0].company_id):
                self.assertEqual(x.scope, inner_scope)
            for p in demo_partners:
                self.assertEqual(p.scope, inner_scope)

            # demo user cannot modify company data, whatever the scope of the record
            with self.assertRaises(except_orm):
                partners[0].company_id.write({'name': 'Pricks'})
            with self.assertRaises(except_orm):
                demo_partners[0].company_id.write({'name': 'Pricks'})

            # remove demo user from all groups, such that it cannot read partner data
            with scope.SUDO():
                demo.write({'groups_id': [(5,)]})

            # demo user can no longer access partner data
            with self.assertRaises(except_orm):
                demo_partners[0].company_id.name
            # but it can still read partner data from the outer scope
            partners[0].company_id.name

    @mute_logger('openerp.osv.orm')
    def test_60_cache(self):
        """ Check the record cache behavior """
        partners = self.Partner.search([('child_ids', '!=', False)])
        partner1, partner2 = partners[0], partners[1]
        children1, children2 = partner1.child_ids, partner2.child_ids
        self.assertTrue(children1)
        self.assertTrue(children2)

        # take a child contact
        child = children1[0]
        self.assertEqual(child.parent_id, partner1)
        self.assertIn(child, partner1.child_ids)
        self.assertNotIn(child, partner2.child_ids)

        # fetch data in the cache
        for p in partners:
            p.name, p.company_id.name, p.user_id.name, p.contact_address
        scope.cache.check()

        # change its parent
        child.write({'parent_id': partner2.id})
        scope.cache.check()

        # check recordsets
        self.assertEqual(child.parent_id, partner2)
        self.assertNotIn(child, partner1.child_ids)
        self.assertIn(child, partner2.child_ids)
        self.assertEqual(set(partner1.child_ids + child), set(children1))
        self.assertEqual(set(partner2.child_ids), set(children2 + child))
        scope.cache.check()

        # delete it
        child.unlink()
        scope.cache.check()

        # check recordsets
        self.assertEqual(set(partner1.child_ids), set(children1) - set([child]))
        self.assertEqual(set(partner2.child_ids), set(children2))
        scope.cache.check()

    @mute_logger('openerp.osv.orm')
    def test_70_record_recordset(self):
        """ Check properties record and recordset. """
        ps = self.Partner.search([('name', 'ilike', 'a')], limit=1)
        self.assertEqual(ps.recordset(), ps)
        p = ps.record()
        self.assertEqual(p, ps[0])
        self.assertEqual(p.recordset(), ps)

        ps = self.Partner.recordset()
        self.assertEqual(ps.recordset(), ps)
        for p in ps:
            self.assertIsInstance(p.id, (int, long))

    @mute_logger('openerp.osv.orm')
    def test_80_contains(self):
        """ Test membership on recordset. """
        ps = self.Partner.search([('name', 'ilike', 'a')], limit=1)
        p = ps.record()
        ps = self.Partner.search([('name', 'ilike', 'a')])
        self.assertTrue(p in ps)

    @mute_logger('openerp.osv.orm')
    def test_80_concat(self):
        """ Check concatenation of recordsets. """
        pa = self.Partner.search([('name', 'ilike', 'a')])
        pb = self.Partner.search([('name', 'ilike', 'b')])
        pab = pa + pb
        self.assertEqual(list(pab), list(pa) + list(pb))
