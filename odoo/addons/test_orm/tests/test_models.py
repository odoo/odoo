from pprint import pformat

from odoo import Command, models
from odoo.exceptions import AccessError, LockError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import SQL, lazy, mute_logger, unique

from .common import TestOrmPartnerCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestORM(TransactionCase):
    """ test special behaviors of ORM CRUD functions """

    @mute_logger('odoo.models')
    def test_access_deleted_records(self):
        """ Verify that accessing deleted records works as expected """
        c1 = self.env['res.partner.category'].create({'name': 'W'})
        c2 = self.env['res.partner.category'].create({'name': 'Y'})
        c1.unlink()

        # read() is expected to skip deleted records because our API is not
        # transactional for a sequence of search()->read() performed from the
        # client-side... a concurrent deletion could therefore cause spurious
        # exceptions even when simply opening a list view!
        # /!\ Using unprileged user to detect former side effects of ir.rules!
        user = self.env['res.users'].create({
            'name': 'test user',
            'login': 'test2',
            'group_ids': [Command.set([self.ref('base.group_user')])],
        })
        cs = (c1 + c2).with_user(user)
        self.assertEqual([{'id': c2.id, 'name': 'Y'}], cs.read(['name']), "read() should skip deleted records")
        self.assertEqual([], cs[0].read(['name']), "read() should skip deleted records")

        # Deleting an already deleted record should be simply ignored
        self.assertTrue(c1.unlink(), "Re-deleting should be a no-op")

    @mute_logger('odoo.models')
    def test_access_partial_deletion(self):
        """ Check accessing a record from a recordset where another record has been deleted. """
        Model = self.env['res.country']
        display_name_field = Model._fields['display_name']
        self.assertTrue(display_name_field.compute and not display_name_field.store, "test assumption not satisfied")

        # access regular field when another record from the same prefetch set has been deleted
        records = Model.create([{'name': name[0], 'code': name[1]} for name in (['Foo', 'ZV'], ['Bar', 'ZX'], ['Baz', 'ZY'])])
        for record in records:
            record.name
            record.unlink()

        # access computed field when another record from the same prefetch set has been deleted
        records = Model.create([{'name': name[0], 'code': name[1]} for name in (['Foo', 'ZV'], ['Bar', 'ZX'], ['Baz', 'ZY'])])
        for record in records:
            record.display_name
            record.unlink()

    @mute_logger('odoo.models', 'odoo.addons.base.models.ir_rule')
    def test_access_filtered_records(self):
        """ Verify that accessing filtered records works as expected for non-admin user """
        p1 = self.env['res.partner'].create({'name': 'W'})
        p2 = self.env['res.partner'].create({'name': 'Y'})
        user = self.env['res.users'].create({
            'name': 'test user',
            'login': 'test2',
            'group_ids': [Command.set([self.ref('base.group_user')])],
        })

        partner_model = self.env['ir.model'].search([('model','=','res.partner')])
        self.env['ir.rule'].create({
            'name': 'Y is invisible',
            'domain_force': [('id', '!=', p1.id)],
            'model_id': partner_model.id,
        })

        # search as unprivileged user
        partners = self.env['res.partner'].with_user(user).search([])
        self.assertNotIn(p1, partners, "W should not be visible...")
        self.assertIn(p2, partners, "... but Y should be visible")

        # read as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).read(['name'])
        # write as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).write({'name': 'foo'})
        # unlink as unprivileged user
        with self.assertRaises(AccessError):
            p1.with_user(user).unlink()

        # Prepare mixed case 
        p2.unlink()
        # read mixed records: some deleted and some filtered
        with self.assertRaises(AccessError):
            (p1 + p2).with_user(user).read(['name'])
        # delete mixed records: some deleted and some filtered
        with self.assertRaises(AccessError):
            (p1 + p2).with_user(user).unlink()

    def test_read(self):
        partner = self.env['res.partner'].create({'name': 'MyPartner1'})
        result = partner.read()
        self.assertIsInstance(result, list)

    @mute_logger('odoo.models')
    def test_search_read(self):
        partner = self.env['res.partner']

        # simple search_read
        partner.create({'name': 'MyPartner1'})
        found = partner.search_read([('name', '=', 'MyPartner1')], ['name'])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['name'], 'MyPartner1')
        self.assertIn('id', found[0])

        # search_read correct order
        partner.create({'name': 'MyPartner2'})
        found = partner.search_read([('name', 'like', 'MyPartner')], ['name'], order="name")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['name'], 'MyPartner1')
        self.assertEqual(found[1]['name'], 'MyPartner2')
        found = partner.search_read([('name', 'like', 'MyPartner')], ['name'], order="name desc")
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['name'], 'MyPartner2')
        self.assertEqual(found[1]['name'], 'MyPartner1')

        # search_read that finds nothing
        found = partner.search_read([('name', '=', 'Does not exists')], ['name'])
        self.assertEqual(len(found), 0)

        # search_read with an empty array of fields
        found = partner.search_read([], [], limit=1)
        self.assertEqual(len(found), 1)
        self.assertTrue(field in list(found[0]) for field in ['id', 'name', 'display_name', 'email'])

        # search_read without fields
        found = partner.search_read([], False, limit=1)
        self.assertEqual(len(found), 1)
        self.assertTrue(field in list(found[0]) for field in ['id', 'name', 'display_name', 'email'])

    @mute_logger('odoo.sql_db')
    def test_exists(self):
        partner = self.env['res.partner']

        # check that records obtained from search exist
        recs = partner.search([])
        self.assertTrue(recs)
        self.assertEqual(recs.exists(), recs)

        # check that new records exist by convention
        recs = partner.new({})
        self.assertTrue(recs.exists())

        # check that there is no record with id -1
        # (it is technically valid, but should not exist)
        recs = partner.browse([-1])
        self.assertFalse(recs.exists())

    def test_lock_for_update(self):
        partner = self.env['res.partner']
        p1, p2 = partner.search([], limit=2)

        # lock p1
        p1.lock_for_update(allow_referencing=True)
        p1.lock_for_update(allow_referencing=False)

        with self.env.registry.cursor() as cr:
            recs = (p1 + p2).with_env(partner.env(cr=cr))
            with self.assertRaises(LockError):
                recs.lock_for_update()
            sub_p2 = recs[1]
            sub_p2.lock_for_update()

            # parent transaction and read, but cannot lock the p2 records
            p2.invalidate_model()
            self.assertTrue(p2.name)
            with self.assertRaises(LockError):
                p2.lock_for_update()

            # can still read from parent after locks and lock failures
            p1.invalidate_model()
            self.assertTrue(p1.name)

        # can lock p2 now
        p2.lock_for_update()

        # cannot lock inexisting record
        inexisting = partner.create({'name': 'inexisting'})
        inexisting.unlink()
        self.assertFalse(inexisting.exists())
        with self.assertRaises(LockError):
            inexisting.lock_for_update()

    def test_try_lock_for_update(self):
        partner = self.env['res.partner']
        p1, p2, *_other = recs = partner.search([], limit=4)

        # lock p1
        self.assertEqual(p1.try_lock_for_update(allow_referencing=True), p1)
        self.assertEqual(p1.try_lock_for_update(allow_referencing=False), p1)

        with self.env.registry.cursor() as cr:
            sub_recs = (p1 + p2).with_env(partner.env(cr=cr))
            self.assertEqual(sub_recs.try_lock_for_update(), sub_recs[1])

        self.assertEqual(recs.try_lock_for_update(limit=1), p1)
        self.assertEqual(recs.try_lock_for_update(), recs)

        # check that order is preserved when limiting
        self.assertEqual(recs[::-1].try_lock_for_update(limit=1), recs[-1])

    def test_write_duplicate(self):
        p1 = self.env['res.partner'].create({'name': 'W'})
        (p1 + p1).write({'name': 'X'})

    def test_m2m_store_trigger(self):
        group_user = self.env.ref('base.group_user')

        user = self.env['res.users'].create({
            'name': 'test',
            'login': 'test_m2m_store_trigger',
            'group_ids': [Command.set([])],
        })
        self.assertTrue(user.share)

        group_user.write({'user_ids': [Command.link(user.id)]})
        self.assertFalse(user.share)

        group_user.write({'user_ids': [Command.unlink(user.id)]})
        self.assertTrue(user.share)

    def test_create_multi(self):
        """ create for multiple records """
        # create countries and states
        vals_list = [{
            'name': 'Foo',
            'state_ids': [
                Command.create({'name': 'North Foo', 'code': 'NF'}),
                Command.create({'name': 'South Foo', 'code': 'SF'}),
                Command.create({'name': 'West Foo', 'code': 'WF'}),
                Command.create({'name': 'East Foo', 'code': 'EF'}),
            ],
            'code': 'ZV',
        }, {
            'name': 'Bar',
            'state_ids': [
                Command.create({'name': 'North Bar', 'code': 'NB'}),
                Command.create({'name': 'South Bar', 'code': 'SB'}),
            ],
            'code': 'ZX',
        }]
        foo, bar = self.env['res.country'].create(vals_list)
        self.assertEqual(foo.name, 'Foo')
        self.assertCountEqual(foo.mapped('state_ids.code'), ['NF', 'SF', 'WF', 'EF'])
        self.assertEqual(bar.name, 'Bar')
        self.assertCountEqual(bar.mapped('state_ids.code'), ['NB', 'SB'])


@tagged('at_install', '-post_install')
class TestRecordset(TestOrmPartnerCommon, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._load_partners_set()

    @mute_logger('odoo.models')
    def test_recordset_immutability(self):
        partners = self.partners
        self.assertTrue(partners)

        ids = partners.ids

        partners.write({'active': False})

        # The recordset doesn't change.
        self.assertEqual(ids, partners.ids)

        # After a new search, the recordset changed.
        partners = self.env['test_orm.partner'].search([('id', 'in', self.partners.ids)])
        self.assertFalse(partners)

    @mute_logger('odoo.models')
    def test_relational_fields(self):
        partner = self.partners[0]

        self.assertIsRecord(partner, 'test_orm.partner')
        self.assertIsRecord(partner.country_id, 'test_orm.country')
        self.assertIsRecordset(partner.category_id, 'test_orm.partner.category')

        partner_fields = dict(self.partners._fields.items())

        self.assertEqual(partner_fields['parent_id'].type, 'many2one')
        self.assertIsRecord(partner.parent_id, partner_fields['parent_id'].comodel_name)

        self.assertEqual(partner_fields['child_ids'].type, 'one2many')
        self.assertIsRecordset(partner.child_ids, partner_fields['child_ids'].comodel_name)

        self.assertEqual(partner_fields['category_id'].type, 'many2many')
        self.assertIsRecordset(partner.category_id, partner_fields['category_id'].comodel_name)

    @mute_logger('odoo.models')
    def test_empty_recordsets(self):
        partner = self.partners.filtered_domain([('parent_id', '=', False)])[0]
        self.assertEqual(len(partner), 1)
        self.assertIsRecord(partner, 'test_orm.partner')

        self.assertFalse(partner.parent_id)
        self.assertFalse(partner.parent_id.id)
        self.assertIsEmptyRecordset(partner.parent_id, 'test_orm.partner')

        self.assertFalse(partner.parent_id.country_id)
        self.assertFalse(partner.parent_id.country_id.name)
        self.assertIsEmptyRecordset(partner.parent_id.country_id, 'test_orm.country')

        self.assertFalse(partner.parent_id.category_id)
        self.assertFalse(partner.parent_id.category_id.name)
        self.assertIsRecordset(partner.parent_id.category_id, 'test_orm.partner.category')

    @mute_logger('odoo.models')
    def test_recordset_write(self):
        partners = self.partners
        self.assertTrue(partners)

        partners.write({'active': False})

        for partner in partners:
            self.assertFalse(partner.active)

    @mute_logger('odoo.models')
    def test_record_write(self):
        partners = self.partners
        self.assertTrue(partners)

        for partner in partners:
            partner.write({'active': False})

        for partner in partners:
            self.assertFalse(partner.active)

    @mute_logger('odoo.models')
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_recordset_environment(self):
        partners = self.partners.filtered_domain([('name', 'ilike', 'j')])
        self.assertTrue(partners)

        # Partners and reachable records are attached to self.env
        self.assertEqual(partners.env, self.env)
        for record in (partners, partners[0], partners[0].country_id):
            self.assertEqual(record.env, self.env)
        for partner in partners:
            self.assertEqual(partner.env, self.env)

        # Create a new environment
        demo = self.env['res.users'].create({
            'name': 'test_environment_demo',
            'login': 'test_environment_demo',
            'password': 'test_environment_demo',
        })
        demo_env = self.env(user=demo)
        self.assertNotEqual(demo_env, self.env)

        # Partners and reachable records are still attached to self.env
        self.assertEqual(partners.env, self.env)
        for record in (partners, partners[0], partners[0].country_id):
            self.assertEqual(record.env, self.env)
        for partner in partners:
            self.assertEqual(partner.env, self.env)

        # Create record instances attached to demo_env
        demo_partners = partners.with_user(demo)
        self.assertEqual(demo_partners.env, demo_env)
        for x in (demo_partners, demo_partners[0], demo_partners[0].country_id):
            self.assertEqual(x.env, demo_env)
        for p in demo_partners:
            self.assertEqual(p.env, demo_env)

    @mute_logger('odoo.models')
    def test_record_cache_behavior(self):
        names = {
            'partner One': ['Partner One - One', 'Partner One - Two'],
            'Partner Two': ['Partner Two - One'],
            'Partner Three': ['Partner Three - One'],
        }
        partners = self.env['test_orm.partner'].create([{
            'name': name,
            'child_ids': [Command.create({'name': child_name}) for child_name in children_names],
        } for name, children_names in names.items()])

        partner1, partner2 = partners[0], partners[1]
        children1, children2 = partner1.child_ids, partner2.child_ids
        self.assertTrue(children1)
        self.assertTrue(children2)

        # Take a child contact
        child = children1[0]
        self.assertEqual(child.parent_id, partner1)
        self.assertIn(child, partner1.child_ids)
        self.assertNotIn(child, partner2.child_ids)

        # Fetch data in the cache
        for p in partners:
            # p.name, p.company_id.name, p.user_id.name, p.contact_address
            p.name, p.state_id.name, p.vat
        self.check_cache_consistency()

        # Change its parent
        child.write({'parent_id': partner2.id})
        self.check_cache_consistency()

        # Check recordsets
        self.assertEqual(child.parent_id, partner2)
        self.assertNotIn(child, partner1.child_ids)
        self.assertIn(child, partner2.child_ids)
        self.assertEqual(set(partner1.child_ids + child), set(children1))
        self.assertEqual(set(partner2.child_ids), set(children2 + child))
        self.check_cache_consistency()

        # Delete it
        child.unlink()
        self.check_cache_consistency()

        # Check recordsets
        self.assertEqual(set(partner1.child_ids), set(children1) - {child})
        self.assertEqual(set(partner2.child_ids), set(children2))
        self.check_cache_consistency()

        # Convert from the cache format to the write format
        partner = partner1
        partner.country_id, partner.child_ids
        data = partner._convert_to_write(partner._cache)
        self.assertEqual(data['country_id'], partner.country_id.id)
        self.assertEqual(data['child_ids'], [Command.set(partner.child_ids.ids)])

    def check_cache_consistency(self):
        env = self.env
        depends_context = env.registry.field_depends_context
        invalids = []

        def process(model, field, field_cache):
            # ignore new records and records to flush
            dirty_ids = env.transaction.field_dirty.get(field, ())
            ids = [id_ for id_ in field_cache if id_ and id_ not in dirty_ids]
            if not ids:
                return

            # select the column for the given ids
            query = models.Query(model)
            sql_id = query.table.id
            sql_field = query.table[field.name]
            if field.type == 'binary' and (
                    model.env.context.get('bin_size') or model.env.context.get('bin_size_' + field.name)
            ):
                sql_field = SQL('pg_size_pretty(length(%s)::bigint)', sql_field)
            query.add_where(SQL("%s IN %s", sql_id, tuple(ids)))
            env.cr.execute(query.select(sql_id, sql_field))

            # compare returned values with corresponding values in cache
            for id_, value in env.cr.fetchall():
                cached = field_cache[id_]
                if value == cached or (not value and not cached):
                    continue
                invalids.append((model.browse((id_,)), field, {'cached': cached, 'fetched': value}))

        for field, field_cache in env.transaction.field_data.items():
            # check column fields only
            if not field.store or not field.column_type or field.translate or field.company_dependent:
                continue

            model = env[field.model_name]
            if field in depends_context:
                for context_keys, inner_cache in field_cache.items():
                    context = dict(zip(depends_context[field], context_keys))
                    if 'company' in context:
                        # the cache key 'company' actually comes from context
                        # key 'allowed_company_ids' (see property env.company
                        # and method env.cache_key())
                        context['allowed_company_ids'] = [context.pop('company')]
                    process(model.with_context(context), field, inner_cache)
            else:
                process(model, field, field_cache)

        if invalids:
            self.fail("Invalid cache: %s" % pformat(invalids))

    @mute_logger('odoo.models')
    def test_record_cache_prefetching(self):
        partners = self.partners
        self.assertGreater(len(partners), 1)

        # All the records in partners are ready for prefetching
        self.assertCountEqual(partners.ids, partners._prefetch_ids)

        # Reading ONE partner should fetch them ALL
        state = partners[0].state_id
        partner_ids_with_field = [partner.id for partner in partners if 'state_id' in partner._cache]
        self.assertCountEqual(partner_ids_with_field, partners.ids)

        # Partners' states are ready for prefetching
        state_ids = {
            partner._cache['state_id']
            for partner in partners
            if partner._cache['state_id'] is not None
        }

        self.assertGreater(len(state_ids), 1)
        self.assertEqual(state_ids, set(state._prefetch_ids))

        # Reading ONE partner country should fetch ALL partners' countries
        partners[0].state_id.name
        state_ids_with_field = [state.id for state in partners.state_id if 'name' in state._cache]
        self.assertCountEqual(state_ids_with_field, state_ids)

    def test_recordset_reversed(self):
        partners = self.partners
        self.assertGreater(len(partners), 1)

        # Check order
        self.assertEqual(list(reversed(partners)), list(reversed(list(partners))))

        first = next(iter(partners))
        self.assertEqual(first, partners[0])

        last = next(reversed(partners))
        self.assertEqual(last, partners[-1])

        # Check prefetching
        prefetch_ids = partners.ids
        reversed_ids = [partner.id for partner in reversed(partners)]

        self.assertEqual(list(first._prefetch_ids), prefetch_ids)
        self.assertEqual(list(last._prefetch_ids), reversed_ids)

        self.assertEqual(list(reversed(first._prefetch_ids)), reversed_ids)
        self.assertEqual(list(reversed(last._prefetch_ids)), prefetch_ids)

        # Check prefetching across many2one field
        self.assertTrue(partners.state_id.ids)

        prefetch_ids = list(unique(partners.state_id.ids))

        reversed_ids = list(unique(
            partner.state_id.id
            for partner in reversed(partners)
            if partner.state_id
        ))

        self.assertEqual(list(unique(first.state_id._prefetch_ids)), prefetch_ids)
        self.assertEqual(list(unique(last.state_id._prefetch_ids)), reversed_ids)

        self.assertEqual(list(unique(reversed(first.state_id._prefetch_ids))), reversed_ids)
        self.assertEqual(list(unique(reversed(last.state_id._prefetch_ids))), prefetch_ids)

        # Check prefetching across x2many field
        self.assertTrue(partners.child_ids.ids)

        prefetch_ids = partners.child_ids.ids
        reversed_ids = [
            child.id
            for partner in reversed(partners)
            for child in partner.child_ids
        ]

        self.assertEqual(list(first.child_ids._prefetch_ids), prefetch_ids)
        self.assertEqual(list(last.child_ids._prefetch_ids), reversed_ids)

        self.assertEqual(list(reversed(first.child_ids._prefetch_ids)), reversed_ids)
        self.assertEqual(list(reversed(last.child_ids._prefetch_ids)), prefetch_ids)

    @mute_logger('odoo.models')
    def test_ensure_one(self):
        partners = self.partners
        self.assertGreater(len(partners), 1)

        with self.assertRaises(ValueError):
            partners.ensure_one()

        partner = partners[0]
        self.assertEqual(len(partner), 1)
        self.assertEqual(partner.ensure_one(), partner)

        partner_null = self.env['test_orm.partner'].browse()
        self.assertEqual(len(partner_null), 0)

        with self.assertRaises(ValueError):
            partner_null.ensure_one()

    @mute_logger('odoo.models')
    def test_recordset_contains(self):
        partners = self.partners
        self.assertTrue(partners)

        partner = self.partners[0]
        self.assertTrue(partner)

        # Partners contains record (partner)
        self.assertTrue(partner in partners)

        # Partners doesn't contain record
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: ir\.ui\.menu.* in test_orm\.partner.*"):
            _ = self.env['ir.ui.menu'] in partners

        # Partners doesn't contain field
        with self.assertRaisesRegex(TypeError, r"unsupported operand types in: 42 in test_orm\.partner.*"):
            _ = 42 in partners

    @mute_logger('odoo.models')
    def test_recordset_contains_on_lazy(self):
        partners = lazy(lambda: self.partners)
        self.assertTrue(partners)

        partner = lazy(lambda: self.partners[0])
        self.assertTrue(partner)

        # Partners contains record (partner)
        self.assertTrue(partner in partners)

        # Partners doesn't contain record
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: ir\.ui\.menu.* in test_orm\.partner.*"):
            _ = lazy(lambda: self.env['ir.ui.menu']) in partners

        # Partners doesn't contain field
        with self.assertRaisesRegex(TypeError, r"unsupported operand types in: 42 in test_orm\.partner.*"):
            _ = lazy(lambda: 42) in partners

    @mute_logger('odoo.models')
    def test_recordset_set_operations(self):
        partners_a = self.partners.filtered_domain([('name', 'ilike', 'a')])
        self.assertTrue(partners_a)

        partners_b = self.partners.filtered_domain([('name', 'ilike', 'b')])
        self.assertTrue(partners_b)

        concat = partners_a + partners_b
        self.assertEqual(list(concat), list(partners_a) + list(partners_b))
        self.assertEqual(len(concat), len(partners_a) + len(partners_b))

        difference = partners_a - partners_b
        self.assertEqual(len(difference), len(set(difference)))
        self.assertEqual(set(difference), set(partners_a) - set(partners_b))
        self.assertLessEqual(difference, partners_a)

        intersection = partners_a & partners_b
        self.assertTrue(set(partners_a) & set(partners_b))
        self.assertEqual(len(intersection), len(set(intersection)))
        self.assertEqual(set(intersection), set(partners_a) & set(partners_b))
        self.assertLessEqual(intersection, partners_a)
        self.assertLessEqual(intersection, partners_b)

        union = partners_a | partners_b
        self.assertEqual(len(union), len(set(union)))
        self.assertEqual(set(union), set(partners_a) | set(partners_b))
        self.assertGreaterEqual(union, partners_a)
        self.assertGreaterEqual(union, partners_b)

        # Set operations do not work between different models.
        other_model = self.env['test_orm.country.state'].search([])
        self.assertNotEqual(partners_a._name, other_model._name)
        self.assertNotEqual(partners_a, other_model)

        with self.assertRaisesRegex(TypeError, r"unsupported operand types in: test_orm\.partner.* \+ 'string'"):
            _ = partners_a + 'string'
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: test_orm\.partner.* \+ test_orm\.country\.state.*"):
            _ = partners_a + other_model
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: test_orm\.partner.* - test_orm\.country\.state.*"):
            _ = partners_a - other_model
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: test_orm\.partner.* & test_orm\.country\.state.*"):
            _ = partners_a & other_model
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: test_orm\.partner.* \| test_orm\.country\.state.*"):
            _ = partners_a | other_model
        with self.assertRaises(TypeError):
            _ = partners_a < other_model
        with self.assertRaises(TypeError):
            _ = partners_a <= other_model
        with self.assertRaises(TypeError):
            _ = partners_a > other_model
        with self.assertRaises(TypeError):
            _ = partners_a >= other_model

    @mute_logger('odoo.models')
    def test_set_operations_on_lazy(self):
        partners_a = lazy(lambda: self.partners.filtered_domain([('name', 'ilike', 'a')]))
        self.assertTrue(partners_a)

        partners_b = lazy(lambda: self.partners.filtered_domain([('name', 'ilike', 'b')]))
        self.assertTrue(partners_b)

        concat = partners_a + partners_b
        self.assertEqual(list(concat), list(partners_a) + list(partners_b))
        self.assertEqual(len(concat), len(partners_a) + len(partners_b))

        difference = partners_a - partners_b
        self.assertEqual(len(difference), len(set(difference)))
        self.assertEqual(set(difference), set(partners_a) - set(partners_b))
        self.assertLessEqual(difference, partners_a)

        intersection = partners_a & partners_b
        self.assertTrue(set(partners_a) & set(partners_b))
        self.assertEqual(len(intersection), len(set(intersection)))
        self.assertEqual(set(intersection), set(partners_a) & set(partners_b))
        self.assertLessEqual(intersection, partners_a)
        self.assertLessEqual(intersection, partners_b)

        union = partners_a | partners_b
        self.assertEqual(len(union), len(set(union)))
        self.assertEqual(set(union), set(partners_a) | set(partners_b))
        self.assertGreaterEqual(union, partners_a)
        self.assertGreaterEqual(union, partners_b)

        # Set operations do not work between different models.
        other_model = lazy(lambda: self.env['test_orm.country.state'].search([]))
        self.assertNotEqual(partners_a._name, other_model._name)
        self.assertNotEqual(partners_a, other_model)

        with self.assertRaisesRegex(TypeError, r"unsupported operand types in: test_orm\.partner.* \+ 'string'"):
            _ = partners_a + 'string'
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: test_orm\.partner.* \+ test_orm\.country\.state.*"):
            _ = partners_a + other_model
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: test_orm\.partner.* - test_orm\.country\.state.*"):
            _ = partners_a - other_model
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: test_orm\.partner.* & test_orm\.country\.state.*"):
            _ = partners_a & other_model
        with self.assertRaisesRegex(TypeError, r"inconsistent models in: test_orm\.partner.* \| test_orm\.country\.state.*"):
            _ = partners_a | other_model
        with self.assertRaises(TypeError):
            _ = partners_a < other_model
        with self.assertRaises(TypeError):
            _ = partners_a <= other_model
        with self.assertRaises(TypeError):
            _ = partners_a > other_model
        with self.assertRaises(TypeError):
            _ = partners_a >= other_model

    @mute_logger('odoo.models')
    def test_recordset_filtered(self):
        partners = self.partners
        self.assertTrue(partners)

        # Filtered on a single field
        partners_filtered = partners.browse([p.id for p in partners if p.state_id])
        self.assertTrue(partners_filtered)
        self.assertLess(len(partners_filtered), len(partners))
        self.assertEqual(partners.filtered(lambda p: p.state_id), partners_filtered)
        self.assertEqual(partners.filtered('state_id'), partners_filtered)

        # Filtered on a sequence of fields
        partners_filtered = partners.browse([p.id for p in partners if p.parent_id.state_id])
        self.assertTrue(partners_filtered)
        self.assertLess(len(partners_filtered), len(partners))
        self.assertEqual(partners.filtered(lambda p: p.parent_id.state_id), partners_filtered)
        self.assertEqual(partners.filtered('parent_id.state_id'), partners_filtered)

    @mute_logger('odoo.models')
    def test_recordset_mapped(self):
        partners = self.partners

        parents = partners.browse()

        for partner in partners:
            parents |= partner.parent_id

        self.assertGreater(len(parents), 1)

        # Single field
        self.assertEqual(partners.parent_id, parents)
        self.assertEqual(partners.mapped(lambda p: p.parent_id), parents)
        self.assertEqual(partners.mapped('parent_id'), parents)

        # Sequence field
        self.assertEqual(partners.mapped(lambda p: p.parent_id.name), [p.parent_id.name for p in partners])
        self.assertEqual(partners.mapped('parent_id.name'), [p.name for p in parents])
        self.assertEqual(partners.parent_id.mapped('name'), [p.name for p in parents])

        # Empty field
        self.assertEqual(partners.mapped(''), partners)

    @mute_logger('odoo.models')
    def test_recordset_sorted(self):
        partners = self.partners
        self.assertGreater(len(partners), 1)

        # Sort by model order
        partners_shuffled = partners[len(partners) // 2:] + partners[:len(partners) // 2]
        self.assertNotEqual(partners_shuffled.ids, partners.ids)
        self.assertEqual(partners_shuffled.sorted().ids, partners.ids)

        # Sort by name, with a function or a field name
        by_name_ids = [p.id for p in sorted(partners, key=lambda p: p.name)]
        self.assertEqual(partners.sorted(lambda p: p.name).ids, by_name_ids)
        self.assertEqual(partners.sorted('name').ids, by_name_ids)

        # Sort by reverse name, with a field name
        by_reverse_name_ids = [p.id for p in sorted(partners, key=lambda p: p.name, reverse=True)]
        self.assertEqual(partners.sorted('name', reverse=True).ids, by_reverse_name_ids)

    def test_recordset_grouped(self):
        partners = self.partners
        partners[0].email = '@guest.com'
        partners[1].email = '@host.com'
        partners[2].email = '@guest.com'

        partners_grouped = partners.grouped('email')
        self.assertEqual(partners_grouped['@guest.com'].mapped('name'), ['Inner Works', 'AnalytIQ'])

        with self.assertQueries([]):
            _ = partners_grouped['@host.com'].name
