
from openerp import models
from openerp.tools import mute_logger
from openerp.tests import common
from openerp.exceptions import AccessError


class TestAPI(common.TransactionCase):
    """ test the new API of the ORM """

    def assertIsRecordset(self, value, model):
        self.assertIsInstance(value, models.BaseModel)
        self.assertEqual(value._name, model)

    def assertIsRecord(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertTrue(len(value) <= 1)

    def assertIsNull(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertFalse(value)

    @mute_logger('openerp.models')
    def test_00_query(self):
        """ Build a recordset, and check its contents. """
        domain = [('name', 'ilike', 'j')]
        ids = self.registry('res.partner').search(self.cr, self.uid, domain)
        partners = self.env['res.partner'].search(domain)

        # partners is a collection of browse records corresponding to ids
        self.assertTrue(ids)
        self.assertTrue(partners)

        # partners and its contents are instance of the model
        self.assertIsRecordset(partners, 'res.partner')
        for p in partners:
            self.assertIsRecord(p, 'res.partner')

        self.assertEqual([p.id for p in partners], ids)
        self.assertEqual(self.env['res.partner'].browse(ids), partners)

    @mute_logger('openerp.models')
    def test_01_query_offset(self):
        """ Build a recordset with offset, and check equivalence. """
        partners1 = self.env['res.partner'].search([], offset=10)
        partners2 = self.env['res.partner'].search([])[10:]
        self.assertIsRecordset(partners1, 'res.partner')
        self.assertIsRecordset(partners2, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('openerp.models')
    def test_02_query_limit(self):
        """ Build a recordset with offset, and check equivalence. """
        partners1 = self.env['res.partner'].search([], limit=10)
        partners2 = self.env['res.partner'].search([])[:10]
        self.assertIsRecordset(partners1, 'res.partner')
        self.assertIsRecordset(partners2, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('openerp.models')
    def test_03_query_offset_limit(self):
        """ Build a recordset with offset and limit, and check equivalence. """
        partners1 = self.env['res.partner'].search([], offset=3, limit=7)
        partners2 = self.env['res.partner'].search([])[3:10]
        self.assertIsRecordset(partners1, 'res.partner')
        self.assertIsRecordset(partners2, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('openerp.models')
    def test_05_immutable(self):
        """ Check that a recordset remains the same, even after updates. """
        domain = [('name', 'ilike', 'j')]
        partners = self.env['res.partner'].search(domain)
        self.assertTrue(partners)
        ids = map(int, partners)

        # modify those partners, and check that partners has not changed
        self.registry('res.partner').write(self.cr, self.uid, ids, {'active': False})
        self.assertEqual(ids, map(int, partners))

        # redo the search, and check that the result is now empty
        partners2 = self.env['res.partner'].search(domain)
        self.assertFalse(partners2)

    @mute_logger('openerp.models')
    def test_06_fields(self):
        """ Check that relation fields return records, recordsets or nulls. """
        user = self.registry('res.users').browse(self.cr, self.uid, self.uid)
        self.assertIsRecord(user, 'res.users')
        self.assertIsRecord(user.partner_id, 'res.partner')
        self.assertIsRecordset(user.groups_id, 'res.groups')

        partners = self.env['res.partner'].search([])
        for name, field in partners._fields.iteritems():
            if field.type == 'many2one':
                for p in partners:
                    self.assertIsRecord(p[name], field.comodel_name)
            elif field.type == 'reference':
                for p in partners:
                    if p[name]:
                        self.assertIsRecord(p[name], field.comodel_name)
            elif field.type in ('one2many', 'many2many'):
                for p in partners:
                    self.assertIsRecordset(p[name], field.comodel_name)

    @mute_logger('openerp.models')
    def test_07_null(self):
        """ Check behavior of null instances. """
        # select a partner without a parent
        partner = self.env['res.partner'].search([('parent_id', '=', False)])[0]

        # check partner and related null instances
        self.assertTrue(partner)
        self.assertIsRecord(partner, 'res.partner')

        self.assertFalse(partner.parent_id)
        self.assertIsNull(partner.parent_id, 'res.partner')

        self.assertIs(partner.parent_id.id, False)

        self.assertFalse(partner.parent_id.user_id)
        self.assertIsNull(partner.parent_id.user_id, 'res.users')

        self.assertIs(partner.parent_id.user_id.name, False)

        self.assertFalse(partner.parent_id.user_id.groups_id)
        self.assertIsRecordset(partner.parent_id.user_id.groups_id, 'res.groups')

    @mute_logger('openerp.models')
    def test_10_old_old(self):
        """ Call old-style methods in the old-fashioned way. """
        partners = self.env['res.partner'].search([('name', 'ilike', 'j')])
        self.assertTrue(partners)
        ids = map(int, partners)

        # call method name_get on partners' model, and check its effect
        res = partners._model.name_get(self.cr, self.uid, ids)
        self.assertEqual(len(res), len(ids))
        self.assertEqual(set(val[0] for val in res), set(ids))

    @mute_logger('openerp.models')
    def test_20_old_new(self):
        """ Call old-style methods in the new API style. """
        partners = self.env['res.partner'].search([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # call method name_get on partners itself, and check its effect
        res = partners.name_get()
        self.assertEqual(len(res), len(partners))
        self.assertEqual(set(val[0] for val in res), set(map(int, partners)))

    @mute_logger('openerp.models')
    def test_25_old_new(self):
        """ Call old-style methods on records (new API style). """
        partners = self.env['res.partner'].search([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # call method name_get on partner records, and check its effect
        for p in partners:
            res = p.name_get()
            self.assertTrue(isinstance(res, list) and len(res) == 1)
            self.assertTrue(isinstance(res[0], tuple) and len(res[0]) == 2)
            self.assertEqual(res[0][0], p.id)

    @mute_logger('openerp.models')
    def test_30_new_old(self):
        """ Call new-style methods in the old-fashioned way. """
        partners = self.env['res.partner'].search([('name', 'ilike', 'j')])
        self.assertTrue(partners)
        ids = map(int, partners)

        # call method write on partners' model, and check its effect
        partners._model.write(self.cr, self.uid, ids, {'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('openerp.models')
    def test_40_new_new(self):
        """ Call new-style methods in the new API style. """
        partners = self.env['res.partner'].search([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # call method write on partners itself, and check its effect
        partners.write({'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('openerp.models')
    def test_45_new_new(self):
        """ Call new-style methods on records (new API style). """
        partners = self.env['res.partner'].search([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # call method write on partner records, and check its effects
        for p in partners:
            p.write({'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('openerp.models')
    @mute_logger('openerp.addons.base.ir.ir_model')
    def test_50_environment(self):
        """ Test environment on records. """
        # partners and reachable records are attached to self.env
        partners = self.env['res.partner'].search([('name', 'ilike', 'j')])
        self.assertEqual(partners.env, self.env)
        for x in (partners, partners[0], partners[0].company_id):
            self.assertEqual(x.env, self.env)
        for p in partners:
            self.assertEqual(p.env, self.env)

        # check that the current user can read and modify company data
        partners[0].company_id.name
        partners[0].company_id.write({'name': 'Fools'})

        # create an environment with the demo user
        demo = self.env['res.users'].search([('login', '=', 'demo')])[0]
        demo_env = self.env(user=demo)
        self.assertNotEqual(demo_env, self.env)

        # partners and related records are still attached to self.env
        self.assertEqual(partners.env, self.env)
        for x in (partners, partners[0], partners[0].company_id):
            self.assertEqual(x.env, self.env)
        for p in partners:
            self.assertEqual(p.env, self.env)

        # create record instances attached to demo_env
        demo_partners = partners.sudo(demo)
        self.assertEqual(demo_partners.env, demo_env)
        for x in (demo_partners, demo_partners[0], demo_partners[0].company_id):
            self.assertEqual(x.env, demo_env)
        for p in demo_partners:
            self.assertEqual(p.env, demo_env)

        # demo user can read but not modify company data
        demo_partners[0].company_id.name
        with self.assertRaises(AccessError):
            demo_partners[0].company_id.write({'name': 'Pricks'})

        # remove demo user from all groups
        demo.write({'groups_id': [(5,)]})

        # demo user can no longer access partner data
        with self.assertRaises(AccessError):
            demo_partners[0].company_id.name

    @mute_logger('openerp.models')
    def test_55_draft(self):
        """ Test draft mode nesting. """
        env = self.env
        self.assertFalse(env.in_draft)
        with env.do_in_draft():
            self.assertTrue(env.in_draft)
            with env.do_in_draft():
                self.assertTrue(env.in_draft)
                with env.do_in_draft():
                    self.assertTrue(env.in_draft)
                self.assertTrue(env.in_draft)
            self.assertTrue(env.in_draft)
        self.assertFalse(env.in_draft)

    @mute_logger('openerp.models')
    def test_60_cache(self):
        """ Check the record cache behavior """
        Partners = self.env['res.partner']
        pids = []
        data = {
            'partner One': ['Partner One - One', 'Partner One - Two'],
            'Partner Two': ['Partner Two - One'],
            'Partner Three': ['Partner Three - One'],
        }
        for p in data:
            pids.append(Partners.create({
                'name': p,
                'child_ids': [(0, 0, {'name': c}) for c in data[p]],
            }).id)

        partners = Partners.search([('id', 'in', pids)])
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
        self.env.check_cache()

        # change its parent
        child.write({'parent_id': partner2.id})
        self.env.check_cache()

        # check recordsets
        self.assertEqual(child.parent_id, partner2)
        self.assertNotIn(child, partner1.child_ids)
        self.assertIn(child, partner2.child_ids)
        self.assertEqual(set(partner1.child_ids + child), set(children1))
        self.assertEqual(set(partner2.child_ids), set(children2 + child))
        self.env.check_cache()

        # delete it
        child.unlink()
        self.env.check_cache()

        # check recordsets
        self.assertEqual(set(partner1.child_ids), set(children1) - set([child]))
        self.assertEqual(set(partner2.child_ids), set(children2))
        self.env.check_cache()

    @mute_logger('openerp.models')
    def test_60_cache_prefetching(self):
        """ Check the record cache prefetching """
        self.env.invalidate_all()

        # all the records of an instance already have an entry in cache
        partners = self.env['res.partner'].search([])
        partner_ids = self.env.prefetch['res.partner']
        self.assertEqual(set(partners.ids), set(partner_ids))

        # countries have not been fetched yet; their cache must be empty
        countries = self.env['res.country'].browse()
        self.assertFalse(self.env.prefetch['res.country'])

        # reading ONE partner should fetch them ALL
        countries |= partners[0].country_id
        country_cache = self.env.cache[partners._fields['country_id']]
        self.assertLessEqual(set(partners._ids), set(country_cache))

        # read all partners, and check that the cache already contained them
        country_ids = list(self.env.prefetch['res.country'])
        for p in partners:
            countries |= p.country_id
        self.assertLessEqual(set(countries.ids), set(country_ids))

    @mute_logger('openerp.models')
    def test_70_one(self):
        """ Check method one(). """
        # check with many records
        ps = self.env['res.partner'].search([('name', 'ilike', 'a')])
        self.assertTrue(len(ps) > 1)
        with self.assertRaises(ValueError):
            ps.ensure_one()

        p1 = ps[0]
        self.assertEqual(len(p1), 1)
        self.assertEqual(p1.ensure_one(), p1)

        p0 = self.env['res.partner'].browse()
        self.assertEqual(len(p0), 0)
        with self.assertRaises(ValueError):
            p0.ensure_one()

    @mute_logger('openerp.models')
    def test_80_contains(self):
        """ Test membership on recordset. """
        p1 = self.env['res.partner'].search([('name', 'ilike', 'a')], limit=1).ensure_one()
        ps = self.env['res.partner'].search([('name', 'ilike', 'a')])
        self.assertTrue(p1 in ps)

    @mute_logger('openerp.models')
    def test_80_set_operations(self):
        """ Check set operations on recordsets. """
        pa = self.env['res.partner'].search([('name', 'ilike', 'a')])
        pb = self.env['res.partner'].search([('name', 'ilike', 'b')])
        self.assertTrue(pa)
        self.assertTrue(pb)
        self.assertTrue(set(pa) & set(pb))

        concat = pa + pb
        self.assertEqual(list(concat), list(pa) + list(pb))
        self.assertEqual(len(concat), len(pa) + len(pb))

        difference = pa - pb
        self.assertEqual(len(difference), len(set(difference)))
        self.assertEqual(set(difference), set(pa) - set(pb))
        self.assertLessEqual(difference, pa)

        intersection = pa & pb
        self.assertEqual(len(intersection), len(set(intersection)))
        self.assertEqual(set(intersection), set(pa) & set(pb))
        self.assertLessEqual(intersection, pa)
        self.assertLessEqual(intersection, pb)

        union = pa | pb
        self.assertEqual(len(union), len(set(union)))
        self.assertEqual(set(union), set(pa) | set(pb))
        self.assertGreaterEqual(union, pa)
        self.assertGreaterEqual(union, pb)

        # one cannot mix different models with set operations
        ps = pa
        ms = self.env['ir.ui.menu'].search([])
        self.assertNotEqual(ps._name, ms._name)
        self.assertNotEqual(ps, ms)

        with self.assertRaises(TypeError):
            res = ps + ms
        with self.assertRaises(TypeError):
            res = ps - ms
        with self.assertRaises(TypeError):
            res = ps & ms
        with self.assertRaises(TypeError):
            res = ps | ms
        with self.assertRaises(TypeError):
            res = ps < ms
        with self.assertRaises(TypeError):
            res = ps <= ms
        with self.assertRaises(TypeError):
            res = ps > ms
        with self.assertRaises(TypeError):
            res = ps >= ms

    @mute_logger('openerp.models')
    def test_80_filter(self):
        """ Check filter on recordsets. """
        ps = self.env['res.partner'].search([])
        customers = ps.browse([p.id for p in ps if p.customer])

        # filter on a single field
        self.assertEqual(ps.filtered(lambda p: p.customer), customers)
        self.assertEqual(ps.filtered('customer'), customers)

        # filter on a sequence of fields
        self.assertEqual(
            ps.filtered(lambda p: p.parent_id.customer),
            ps.filtered('parent_id.customer')
        )

    @mute_logger('openerp.models')
    def test_80_map(self):
        """ Check map on recordsets. """
        ps = self.env['res.partner'].search([])
        parents = ps.browse()
        for p in ps: parents |= p.parent_id

        # map a single field
        self.assertEqual(ps.mapped(lambda p: p.parent_id), parents)
        self.assertEqual(ps.mapped('parent_id'), parents)

        # map a sequence of fields
        self.assertEqual(
            ps.mapped(lambda p: p.parent_id.name),
            [p.parent_id.name for p in ps]
        )
        self.assertEqual(
            ps.mapped('parent_id.name'),
            [p.name for p in parents]
        )
