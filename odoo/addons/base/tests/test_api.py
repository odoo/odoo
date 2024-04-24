# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, Command
from odoo.addons.base.tests.common import SavepointCaseWithUserDemo
from odoo.tools import mute_logger
from odoo.exceptions import AccessError


class TestAPI(SavepointCaseWithUserDemo):
    """ test the new API of the ORM """

    @classmethod
    def setUpClass(cls):
        super(TestAPI, cls).setUpClass()
        cls._load_partners_set()

    def assertIsRecordset(self, value, model):
        self.assertIsInstance(value, models.BaseModel)
        self.assertEqual(value._name, model)

    def assertIsRecord(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertTrue(len(value) <= 1)

    def assertIsNull(self, value, model):
        self.assertIsRecordset(value, model)
        self.assertFalse(value)

    @mute_logger('odoo.models')
    def test_00_query(self):
        """ Build a recordset, and check its contents. """
        domain = [('name', 'ilike', 'j'), ('id', 'in', self.partners.ids)]
        partners = self.env['res.partner'].search(domain)

        # partners is a collection of browse records
        self.assertTrue(partners)

        # partners and its contents are instance of the model
        self.assertIsRecordset(partners, 'res.partner')
        for p in partners:
            self.assertIsRecord(p, 'res.partner')

    @mute_logger('odoo.models')
    def test_01_query_offset(self):
        """ Build a recordset with offset, and check equivalence. """
        partners1 = self.env['res.partner'].search([('id', 'in', self.partners.ids)], offset=5)
        partners2 = self.env['res.partner'].search([('id', 'in', self.partners.ids)])[5:]
        self.assertIsRecordset(partners1, 'res.partner')
        self.assertIsRecordset(partners2, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('odoo.models')
    def test_02_query_limit(self):
        """ Build a recordset with offset, and check equivalence. """
        partners1 = self.env['res.partner'].search([('id', 'in', self.partners.ids)], order='id asc', limit=5)
        partners2 = self.env['res.partner'].search([('id', 'in', self.partners.ids)], order='id asc')[:5]
        self.assertIsRecordset(partners1, 'res.partner')
        self.assertIsRecordset(partners2, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('odoo.models')
    def test_03_query_offset_limit(self):
        """ Build a recordset with offset and limit, and check equivalence. """
        partners1 = self.env['res.partner'].search([('id', 'in', self.partners.ids)], order='id asc', offset=3, limit=7)
        partners2 = self.env['res.partner'].search([('id', 'in', self.partners.ids)], order='id asc')[3:10]
        self.assertIsRecordset(partners1, 'res.partner')
        self.assertIsRecordset(partners2, 'res.partner')
        self.assertEqual(list(partners1), list(partners2))

    @mute_logger('odoo.models')
    def test_04_query_count(self):
        """ Test the search method with count=True. """
        self.cr.execute("SELECT COUNT(*) FROM res_partner WHERE active")
        count1 = self.cr.fetchone()[0]
        count2 = self.env['res.partner'].search([], count=True)
        self.assertIsInstance(count1, int)
        self.assertIsInstance(count2, int)
        self.assertEqual(count1, count2)

    @mute_logger('odoo.models')
    def test_05_immutable(self):
        """ Check that a recordset remains the same, even after updates. """
        domain = [('name', 'ilike', 'g'), ('id', 'in', self.partners.ids)]
        partners = self.env['res.partner'].search(domain)
        self.assertTrue(partners)
        ids = partners.ids

        # modify those partners, and check that partners has not changed
        partners.write({'active': False})
        self.assertEqual(ids, partners.ids)

        # redo the search, and check that the result is now empty
        partners2 = self.env['res.partner'].search(domain)
        self.assertFalse(partners2)

    @mute_logger('odoo.models')
    def test_06_fields(self):
        """ Check that relation fields return records, recordsets or nulls. """
        user = self.env.user
        self.assertIsRecord(user, 'res.users')
        self.assertIsRecord(user.partner_id, 'res.partner')
        self.assertIsRecordset(user.groups_id, 'res.groups')

        for name, field in self.partners._fields.items():
            if field.type == 'many2one':
                for p in self.partners:
                    self.assertIsRecord(p[name], field.comodel_name)
            elif field.type == 'reference':
                for p in self.partners:
                    if p[name]:
                        self.assertIsRecord(p[name], field.comodel_name)
            elif field.type in ('one2many', 'many2many'):
                for p in self.partners:
                    self.assertIsRecordset(p[name], field.comodel_name)

    @mute_logger('odoo.models')
    def test_07_null(self):
        """ Check behavior of null instances. """
        # select a partner without a parent
        partner = self.env['res.partner'].search([('parent_id', '=', False), ('id', 'in', self.partners.ids)])[0]

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

    @mute_logger('odoo.models')
    def test_40_new_new(self):
        """ Call new-style methods in the new API style. """
        partners = self.env['res.partner'].search([('name', 'ilike', 'g'), ('id', 'in', self.partners.ids)])
        self.assertTrue(partners)

        # call method write on partners itself, and check its effect
        partners.write({'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('odoo.models')
    def test_45_new_new(self):
        """ Call new-style methods on records (new API style). """
        partners = self.env['res.partner'].search([('name', 'ilike', 'g'), ('id', 'in', self.partners.ids)])
        self.assertTrue(partners)

        # call method write on partner records, and check its effects
        for p in partners:
            p.write({'active': False})
        for p in partners:
            self.assertFalse(p.active)

    @mute_logger('odoo.models')
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_50_environment(self):
        """ Test environment on records. """
        # partners and reachable records are attached to self.env
        partners = self.env['res.partner'].search([('name', 'ilike', 'j'), ('id', 'in', self.partners.ids)])
        self.assertEqual(partners.env, self.env)
        for x in (partners, partners[0], partners[0].company_id):
            self.assertEqual(x.env, self.env)
        for p in partners:
            self.assertEqual(p.env, self.env)

        # check that the current user can read and modify company data
        partners[0].company_id.name
        partners[0].company_id.write({'name': 'Fools'})

        # create an environment with a demo user
        demo = self.env['res.users'].create({
            'name': 'test_environment_demo',
            'login': 'test_environment_demo',
            'password': 'test_environment_demo',
        })
        demo_env = self.env(user=demo)
        self.assertNotEqual(demo_env, self.env)

        # partners and related records are still attached to self.env
        self.assertEqual(partners.env, self.env)
        for x in (partners, partners[0], partners[0].company_id):
            self.assertEqual(x.env, self.env)
        for p in partners:
            self.assertEqual(p.env, self.env)

        # create record instances attached to demo_env
        demo_partners = partners.with_user(demo)
        self.assertEqual(demo_partners.env, demo_env)
        for x in (demo_partners, demo_partners[0], demo_partners[0].company_id):
            self.assertEqual(x.env, demo_env)
        for p in demo_partners:
            self.assertEqual(p.env, demo_env)

        # demo user can read but not modify company data
        demo_partner = self.env['res.partner'].search([('name', '=', 'Landon Roberts')]).with_user(demo)
        self.assertTrue(demo_partner.company_id, 'This partner is supposed to be linked to a company')
        demo_partner.company_id.name
        with self.assertRaises(AccessError):
            demo_partner.company_id.write({'name': 'Pricks'})

        # remove demo user from all groups
        demo.write({'groups_id': [Command.clear()]})

        # demo user can no longer access partner data
        with self.assertRaises(AccessError):
            demo_partner.company_id.name

    def test_56_environment_uid_origin(self):
        """Check the expected behavior of `env.uid_origin`"""
        user_demo = self.user_demo
        user_admin = self.env.ref('base.user_admin')
        self.assertEqual(self.env.uid_origin, None)
        self.assertEqual(self.env['base'].with_user(user_demo).env.uid_origin, user_demo.id)
        self.assertEqual(self.env['base'].with_user(user_demo).with_user(user_admin).env.uid_origin, user_demo.id)
        self.assertEqual(self.env['base'].with_user(user_admin).with_user(user_demo).env.uid_origin, user_admin.id)

    @mute_logger('odoo.models')
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
                'child_ids': [Command.create({'name': c}) for c in data[p]],
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
        self.env.cache.check(self.env)

        # change its parent
        child.write({'parent_id': partner2.id})
        self.env.cache.check(self.env)

        # check recordsets
        self.assertEqual(child.parent_id, partner2)
        self.assertNotIn(child, partner1.child_ids)
        self.assertIn(child, partner2.child_ids)
        self.assertEqual(set(partner1.child_ids + child), set(children1))
        self.assertEqual(set(partner2.child_ids), set(children2 + child))
        self.env.cache.check(self.env)

        # delete it
        child.unlink()
        self.env.cache.check(self.env)

        # check recordsets
        self.assertEqual(set(partner1.child_ids), set(children1) - set([child]))
        self.assertEqual(set(partner2.child_ids), set(children2))
        self.env.cache.check(self.env)

        # convert from the cache format to the write format
        partner = partner1
        partner.country_id, partner.child_ids
        data = partner._convert_to_write(partner._cache)
        self.assertEqual(data['country_id'], partner.country_id.id)
        self.assertEqual(data['child_ids'], [Command.set(partner.child_ids.ids)])

    @mute_logger('odoo.models')
    def test_60_prefetch(self):
        """ Check the record cache prefetching """
        partners = self.env['res.partner'].search([('id', 'in', self.partners.ids)], limit=models.PREFETCH_MAX)
        self.assertTrue(len(partners) > 1)

        # all the records in partners are ready for prefetching
        self.assertItemsEqual(partners.ids, partners._prefetch_ids)

        # reading ONE partner should fetch them ALL
        for partner in partners:
            state = partner.state_id
            break
        partner_ids_with_field = [partner.id
                                  for partner in partners
                                  if 'state_id' in partner._cache]
        self.assertItemsEqual(partner_ids_with_field, partners.ids)

        # partners' states are ready for prefetching
        state_ids = {
            partner._cache['state_id']
            for partner in partners
            if partner._cache['state_id'] is not None
        }
        self.assertTrue(len(state_ids) > 1)
        self.assertItemsEqual(state_ids, state._prefetch_ids)

        # reading ONE partner country should fetch ALL partners' countries
        for partner in partners:
            if partner.state_id:
                partner.state_id.name
                break
        state_ids_with_field = [st.id for st in partners.state_id if 'name' in st._cache]
        self.assertItemsEqual(state_ids_with_field, state_ids)

    @mute_logger('odoo.models')
    def test_60_prefetch_model(self):
        """ Check the prefetching model. """
        partners = self.env['res.partner'].search([('id', 'in', self.partners.ids)], limit=models.PREFETCH_MAX)
        self.assertTrue(partners)

        def same_prefetch(a, b):
            self.assertEqual(set(a._prefetch_ids), set(b._prefetch_ids))

        def diff_prefetch(a, b):
            self.assertNotEqual(set(a._prefetch_ids), set(b._prefetch_ids))

        # the recordset operations below use different prefetch sets
        diff_prefetch(partners, partners.browse())
        diff_prefetch(partners, partners[0])
        diff_prefetch(partners, partners[:5])

        # the recordset operations below share the prefetch set
        same_prefetch(partners, partners.browse(partners.ids))
        same_prefetch(partners, partners.with_user(self.user_demo))
        same_prefetch(partners, partners.with_context(active_test=False))
        same_prefetch(partners, partners[:10].with_prefetch(partners._prefetch_ids))

        # iteration and relational fields should use the same prefetch set
        self.assertEqual(type(partners).country_id.type, 'many2one')
        self.assertEqual(type(partners).bank_ids.type, 'one2many')
        self.assertEqual(type(partners).category_id.type, 'many2many')

        vals0 = {
            'name': 'Empty relational fields',
            'country_id': False,
            'bank_ids': [],
            'category_id': [],
        }
        vals1 = {
            'name': 'Non-empty relational fields',
            'country_id': self.ref('base.be'),
            'bank_ids': [Command.create({'acc_number': 'FOO42'})],
            'category_id': [Command.link(self.partner_category.id)],
        }
        partners = partners.create(vals0) + partners.create(vals1)
        for partner in partners:
            same_prefetch(partner, partners)
            same_prefetch(partner.country_id, partners.country_id)
            same_prefetch(partner.bank_ids, partners.bank_ids)
            same_prefetch(partner.category_id, partners.category_id)

    @mute_logger('odoo.models')
    def test_60_prefetch_read(self):
        """ Check that reading a field computes it on self only. """
        Partner = self.env['res.partner']
        field = type(Partner).company_type
        self.assertTrue(field.compute and not field.store)

        partner1 = Partner.create({'name': 'Foo'})
        partner2 = Partner.create({'name': 'Bar', 'parent_id': partner1.id})
        self.assertEqual(partner1.child_ids, partner2)

        # reading partner1 should not prefetch 'company_type' on partner2
        self.env.clear()
        partner1 = partner1.with_prefetch()
        partner1.read(['company_type'])
        self.assertIn('company_type', partner1._cache)
        self.assertNotIn('company_type', partner2._cache)

        # reading partner1 should not prefetch 'company_type' on partner2
        self.env.clear()
        partner1 = partner1.with_prefetch()
        partner1.read(['child_ids', 'company_type'])
        self.assertIn('company_type', partner1._cache)
        self.assertNotIn('company_type', partner2._cache)

    @mute_logger('odoo.models')
    def test_70_one(self):
        """ Check method one(). """
        # check with many records
        ps = self.env['res.partner'].search([('name', 'ilike', 'a'), ('id', 'in', self.partners.ids)])
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

    @mute_logger('odoo.models')
    def test_80_contains(self):
        """ Test membership on recordset. """
        p1 = self.env['res.partner'].search([('name', 'ilike', 'a'), ('id', 'in', self.partners.ids)], limit=1).ensure_one()
        ps = self.env['res.partner'].search([('name', 'ilike', 'a'), ('id', 'in', self.partners.ids)])
        self.assertTrue(p1 in ps)

    @mute_logger('odoo.models')
    def test_80_set_operations(self):
        """ Check set operations on recordsets. """
        pa = self.env['res.partner'].search([('name', 'ilike', 'a'), ('id', 'in', self.partners.ids)])
        pb = self.env['res.partner'].search([('name', 'ilike', 'b'), ('id', 'in', self.partners.ids)])
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

    @mute_logger('odoo.models')
    def test_80_filter(self):
        """ Check filter on recordsets. """
        ps = self.partners
        customers = ps.browse([p.id for p in ps if p.employee])

        # filter on a single field
        self.assertEqual(ps.filtered(lambda p: p.employee), customers)
        self.assertEqual(ps.filtered('employee'), customers)

        # filter on a sequence of fields
        self.assertEqual(
            ps.filtered(lambda p: p.parent_id.employee),
            ps.filtered('parent_id.employee')
        )

    @mute_logger('odoo.models')
    def test_80_map(self):
        """ Check map on recordsets. """
        ps = self.partners
        parents = ps.browse()
        for p in ps:
            parents |= p.parent_id

        # map a single field
        self.assertEqual(ps.mapped(lambda p: p.parent_id), parents)
        self.assertEqual(ps.mapped('parent_id'), parents)
        self.assertEqual(ps.parent_id, parents)

        # map a sequence of fields
        self.assertEqual(
            ps.mapped(lambda p: p.parent_id.name),
            [p.parent_id.name for p in ps]
        )
        self.assertEqual(
            ps.mapped('parent_id.name'),
            [p.name for p in parents]
        )
        self.assertEqual(
            ps.parent_id.mapped('name'),
            [p.name for p in parents]
        )

        # map an empty sequence of fields
        self.assertEqual(ps.mapped(''), ps)

    @mute_logger('odoo.models')
    def test_80_sorted(self):
        """ Check sorted on recordsets. """
        ps = self.env['res.partner'].search([('id', 'in', self.partners.ids)])

        # sort by model order
        qs = ps[:len(ps) // 2] + ps[len(ps) // 2:]
        self.assertEqual(qs.sorted().ids, ps.ids)

        # sort by name, with a function or a field name
        by_name_ids = [p.id for p in sorted(ps, key=lambda p: p.name)]
        self.assertEqual(ps.sorted(lambda p: p.name).ids, by_name_ids)
        self.assertEqual(ps.sorted('name').ids, by_name_ids)

        # sort by inverse name, with a field name
        by_name_ids = [p.id for p in sorted(ps, key=lambda p: p.name, reverse=True)]
        self.assertEqual(ps.sorted('name', reverse=True).ids, by_name_ids)

        # sorted doesn't filter out new records but don't sort them either (limitation)
        new_p = self.env['res.partner'].new({
            'child_ids': [
                Command.create({'name': 'z'}),
                Command.create({'name': 'a'}),
            ],
        })
        self.assertEqual(len(new_p.child_ids.sorted()), 2)

        # sorted keeps the _prefetch_ids
        partners_with_children = self.env['res.partner'].create([
            {
                'name': 'required',
                'child_ids': [
                    Command.create({'name': 'z'}),
                    Command.create({'name': 'a'}),
                ],
            },
            {
                'name': 'required',
                'child_ids': [
                    Command.create({'name': 'z'}),
                    Command.create({'name': 'a'}),
                ],
            },
        ])
        partners_with_children.invalidate_cache(['name'])
        # Only one query to fetch name of children of each partner
        with self.assertQueryCount(1):
            for partner in partners_with_children:
                partner.child_ids.sorted('id').mapped('name')


class TestExternalAPI(SavepointCaseWithUserDemo):

    def test_call_kw(self):
        """kwargs is not modified by the execution of the call"""
        partner = self.env['res.partner'].create({'name': 'MyPartner1'})
        args = (partner.ids, ['name'])
        kwargs = {'context': {'test': True}}
        api.call_kw(self.env['res.partner'], 'read', args, kwargs)
        self.assertEqual(kwargs, {'context': {'test': True}})
