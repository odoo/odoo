from odoo.api import NewId, SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged, TransactionCase
from odoo.tools.misc import mute_logger


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSudo(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group0 = cls.env['res.groups'].create({'name': "Group 0"})
        cls.group1 = cls.env['res.groups'].create({'name': "Group 1"})
        cls.group2 = cls.env['res.groups'].create({'name': "Group 2"})
        cls.user = cls.env['res.users'].create({
            'login': 'bob',
            'name': "Bob Bobman",
            'group_ids': [Command.set([cls.group2.id, cls.env.ref('base.group_user').id])],
        })


    """ Test the behavior of method sudo(). """
    def test_sudo(self):
        record = self.env['test_access_right.some_obj'].create({'val': 5})
        user1 = self.user
        partner_demo = self.env['res.partner'].create({
            'name': 'Marc Demo',
        })
        user2 = self.env['res.users'].create({
            'login': 'demo2',
            'password': 'demo2',
            'partner_id': partner_demo.id,
            'group_ids': [Command.set([self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
        })

        # with_user(user)
        record1 = record.with_user(user1)
        self.assertEqual(record1.env.uid, user1.id)
        self.assertFalse(record1.env.su)

        record2 = record1.with_user(user2)
        self.assertEqual(record2.env.uid, user2.id)
        self.assertFalse(record2.env.su)

        # the superuser is always in superuser mode
        record3 = record2.with_user(SUPERUSER_ID)
        self.assertEqual(record3.env.uid, SUPERUSER_ID)
        self.assertTrue(record3.env.su)

        # sudo()
        surecord1 = record1.sudo()
        self.assertEqual(surecord1.env.uid, user1.id)
        self.assertTrue(surecord1.env.su)

        surecord2 = record2.sudo()
        self.assertEqual(surecord2.env.uid, user2.id)
        self.assertTrue(surecord2.env.su)

        surecord3 = record3.sudo()
        self.assertEqual(surecord3.env.uid, SUPERUSER_ID)
        self.assertTrue(surecord3.env.su)

        # sudo().sudo()
        surecord1 = surecord1.sudo()
        self.assertEqual(surecord1.env.uid, user1.id)
        self.assertTrue(surecord1.env.su)

        # sudo(False)
        record1 = surecord1.sudo(False)
        self.assertEqual(record1.env.uid, user1.id)
        self.assertFalse(record1.env.su)

        record2 = surecord2.sudo(False)
        self.assertEqual(record2.env.uid, user2.id)
        self.assertFalse(record2.env.su)

        record3 = surecord3.sudo(False)
        self.assertEqual(record3.env.uid, SUPERUSER_ID)
        self.assertTrue(record3.env.su)

        # sudo().with_user(user)
        record2 = surecord1.with_user(user2)
        self.assertEqual(record2.env.uid, user2.id)
        self.assertFalse(record2.env.su)


class Feedback(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group0 = cls.env['res.groups'].create({'name': "Group 0"})
        cls.group1 = cls.env['res.groups'].create({'name': "Group 1"})
        cls.group2 = cls.env['res.groups'].create({'name': "Group 2"})
        cls.user = cls.env['res.users'].create({
            'login': 'bob',
            'name': "Bob Bobman",
            'group_ids': [Command.set([cls.group2.id, cls.env.ref('base.group_user').id])],
        })


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestFieldGroupFeedback(Feedback):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env['test_access_right.some_obj'].create({
            'val': 0,
        }).with_user(cls.user)
        cls.inherits_record = cls.env['test_access_right.inherits'].create({
            'some_id': cls.record.id,
        }).with_user(cls.user)

    @mute_logger('odoo.models')
    def test_read(self):
        self.user.write({
            'group_ids': [Command.set([self.env.ref('base.group_user').id])],
        })
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            _ = self.record.forbidden

        self.assertEqual(
            ctx.exception.args[0],
            f"""You do not have enough rights to access the field "forbidden" on Object For Test Access Right (test_access_right.some_obj). Please contact your system administrator.

Operation: read
User: {self.user.id}
Groups: allowed for groups 'Role / Portal', 'Test Group'""",
        )

        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            _ = self.record.forbidden3

        self.assertEqual(
            ctx.exception.args[0],
            f"""You do not have enough rights to access the field "forbidden3" on Object For Test Access Right (test_access_right.some_obj). Please contact your system administrator.

Operation: read
User: {self.user.id}
Groups: always forbidden""",
        )

    @mute_logger('odoo.models')
    def test_write(self):
        self.user.write({
            'group_ids': [Command.set([self.env.ref('base.group_user').id])],
        })
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'forbidden': 1, 'forbidden2': 2})

        self.assertEqual(
            ctx.exception.args[0],
            f"""You do not have enough rights to access the field "forbidden" on Object For Test Access Right (test_access_right.some_obj). Please contact your system administrator.

Operation: write
User: {self.user.id}
Groups: allowed for groups 'Role / Portal', 'Test Group'""",
        )

    @mute_logger('odoo.models')
    def test_check_field_access_rights_domain(self):
        with self.assertRaises(AccessError):
            self.record.search([('forbidden3', '=', 58)])

        with self.assertRaises(AccessError):
            self.record.search([('parent_id.forbidden3', '=', 58)])

        with self.assertRaises(AccessError):
            self.record.search([('parent_id', 'any', [('forbidden3', '=', 58)])])

        with self.assertRaises(AccessError):
            self.inherits_record.search([('forbidden3', '=', 58)])

    @mute_logger('odoo.models')
    def test_check_field_access_rights_order(self):
        self.record.search([], order='val')

        with self.assertRaises(AccessError):
            self.record.search([], order='forbidden3 DESC')

        with self.assertRaises(AccessError):
            self.record.search([], order='forbidden3')

        with self.assertRaises(AccessError):
            self.record.search([], order='val DESC,    forbidden3       DESC')

    @mute_logger('odoo.models')
    def test_check_field_access_rights_read_group(self):
        self.record._read_group([], ['val'], [])

        with self.assertRaises(AccessError):
            self.record._read_group([('forbidden3', '=', 58)], ['val'])

        with self.assertRaises(AccessError):
            self.record._read_group([('parent_id.forbidden3', '=', 58)], ['val'])

        with self.assertRaises(AccessError):
            self.record._read_group([], ['forbidden3'])

        with self.assertRaises(AccessError):
            self.record._read_group([], [], ['forbidden3:array_agg'])


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSort(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.countries = cls.env['test_orm.country'].create([
            {'name': 'B'},
            {'name': 'A'},
            {'name': 'C'},
        ])
        b, a, c = cls.countries
        cls.cities = cls.env['test_orm.city'].create([
            {'name': 'c2', 'country_id': c.id},
            {'name': 'b1', 'country_id': b.id},
            {'name': 'b2', 'country_id': b.id},
            {'name': 'c1', 'country_id': c.id},
            {'name': 'a1', 'country_id': a.id},
            {'name': 'a2', 'country_id': a.id},
        ])

    def test_basic(self):
        db_result = self.env['test_orm.country'].search([])
        with self.assertQueryCount(1):
            # 1 query to fetch the fields, in practice it is already prefetched
            self.assertEqual(db_result.ids, self.countries.sorted().ids)
        with self.assertQueryCount(0):
            self.assertEqual(db_result[::-1].ids, self.countries.sorted(reverse=True).ids)
        self.assertEqual(
            self.countries.sorted().mapped('name'),
            ['A', 'B', 'C']
        )

    def test_stable(self):
        self.assertEqual(
            self.cities.sorted('name', reverse=True).sorted('country_id.id'),
            self.cities.sorted(lambda c: (-c.country_id.id, c.name), reverse=True),
        )

    def test_basic_m2o(self):
        db_result = self.env['test_orm.city'].search([])
        with self.assertQueryCount(2):
            # 1 query to fetch the fields of both models,
            # in practice at least one is already prefetched or needs to be and the other is likely to be needed too
            self.assertEqual(db_result.ids, self.cities.sorted().ids)
        with self.assertQueryCount(0):
            self.assertEqual(db_result[::-1].ids, self.cities.sorted(reverse=True).ids)
        self.assertEqual(
            self.cities.sorted().mapped('name'),
            ['a1', 'a2', 'b1', 'b2', 'c1', 'c2']
        )

    def test_basic_boolean(self):
        records = self.env['test_orm.model_active_field'].create([{'name': v} for v in 'abc'])
        records[1].active = False
        t_records = records.filtered('active')
        f_records = records - t_records
        with self.assertQueryCount(0):
            records.sorted('active, name')
        self.assertEqual(f_records + t_records, records.sorted('active, name'))
        self.assertEqual(t_records + f_records, records.sorted('active DESC, name'))

    def test_custom_m2o(self):
        order = 'country_id DESC, id ASC'
        db_result = self.env['test_orm.city'].search([], order=order)
        with self.assertQueryCount(2):
            # 1 query to fetch the fields of both models,
            # in practice at least one is already prefetched or needs to be and the other is likely to be needed too
            self.assertEqual(db_result.ids, self.cities.sorted(order).ids)
        with self.assertQueryCount(0):
            self.assertEqual(db_result[::-1].ids, self.cities.sorted(order, reverse=True).ids)
        self.assertEqual(
            self.cities.sorted(order).mapped('name'),
            ['c2', 'c1', 'b1', 'b2', 'a1', 'a2'],
        )

    def test_nulls(self):
        cities = self.env['test_orm.city'].create([
            {'name': 'not null 2', 'country_id': self.countries[2].id},
            {'name': 'not null 0', 'country_id': self.countries[0].id},
            {'name': False, 'country_id': self.countries[1].id},
            {'name': "", 'country_id': False},
            {'name': False, 'country_id': False},
            {'name': 'not null 1', 'country_id': self.countries[1].id},
        ])

        for order in [
            'country_id ASC, id',
            'country_id DESC, id',
            'country_id ASC NULLS FIRST, id',
            'country_id DESC NULLS FIRST, id',
            'country_id ASC NULLS LAST, id',
            'country_id DESC NULLS LAST, id',
            'name ASC, id',
            'name DESC, id',
            'name ASC NULLS FIRST, id',
            'name DESC NULLS FIRST, id',
            'name ASC NULLS LAST, id',
            'name DESC NULLS LAST, id',
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    self.env['test_orm.city'].search([('id', 'in', cities.ids)], order=order).mapped('name'),
                    cities.sorted(order).mapped('name')
                )

    def test_collation(self):
        countries = self.env['test_orm.country'].create([
            {'name': 'é'},
            {'name': 'e'},
            {'name': 'É'},
            {'name': '1.0'},
            {'name': '1,0'},
            {'name': '01'},
            {'name': '10'},
            {'name': '9'},
            {'name': 'Ab'},
            {'name': '👍'},
            {'name': 'AB'},
            {'name': 'Aa'},
            {'name': 'AA'},
        ])

        for order in [
            "name DESC",
            "name ASC",
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    countries.search([('id', 'in', countries.ids)], order=order).mapped('name'),
                    countries.sorted(order).mapped('name')
                )

    def test_sorted_recursion(self):
        categories = self.env['test_orm.category'].search([])
        for order in [
            'parent ASC, id ASC',
            'parent ASC, id DESC',
            'parent DESC, id ASC',
            'parent DESC, id DESC',
        ]:
            with self.subTest(order=order):
                self.assertEqual(
                    categories.search([('id', 'in', categories.ids)], order=order).mapped('name'),
                    categories.sorted(order).mapped('name')
                )

    def test_compare_new_id(self):
        self.assertLess(5, NewId())
        self.assertLess(3, NewId(4))
        self.assertGreater(5, NewId(4))
        self.assertGreaterEqual(5, NewId(4))
        self.assertLess(4, NewId(4))
        self.assertGreater(NewId(5), NewId(4))

    def test_sorted_new_id(self):
        new_countries = self.env['test_orm.country'].concat(*[
            self.env['test_orm.country'].new(vals)
            for vals in [
                {'name': 'B'},
                {'name': 'A'},
                {'name': 'C'},
            ]
        ])

        order = 'id'  # new id after existing ones
        self.assertEqual(
            (self.countries + new_countries).sorted(order),
            self.countries.sorted(order) + new_countries.sorted(order),
        )

        order = 'id DESC'  # new id before existing ones
        self.assertEqual(
            (self.countries + new_countries).sorted(order),
            new_countries.sorted(order) + self.countries.sorted(order),
        )

    def test_prefetch(self):
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
        partners_with_children.invalidate_model(['name'])
        # Only one query to fetch name of children of each partner
        with self.assertQueryCount(1):
            for partner in partners_with_children:
                partner.child_ids.sorted('id').mapped('name')


@tagged('at_install', '-post_install')
class TestCreate(TransactionCase):
    def test_create_multi(self):
        """ create for multiple records """
        vals_list = [{'foo': foo} for foo in ('Foo', 'Bar', 'Baz')]
        vals_list[0]['text'] = 'TEXT EXAMPLE'
        for vals in vals_list:
            record = self.env['test_orm.mixed'].create(vals)
            self.assertEqual(len(record), 1)
            self.assertEqual(record.foo, vals['foo'])
            self.assertEqual(record.text, vals.get('text', False))

        records = self.env['test_orm.mixed'].create([])
        self.assertFalse(records)

        records = self.env['test_orm.mixed'].create(vals_list)
        self.assertEqual(len(records), len(vals_list))
        for record, vals in zip(records, vals_list):
            self.assertEqual(record.foo, vals['foo'])
            self.assertEqual(record.text, vals.get('text', False))
