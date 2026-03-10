# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, LockError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo import Command


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
