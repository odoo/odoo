from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import common


@common.tagged('at_install', '-post_install', 'groups')
class TestGroupsOdoo(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_group = cls.env['res.groups'].create({
            'name': 'test with implied user',
            'implied_ids': [Command.link(cls.env.ref('base.group_user').id)]
        })
        cls.env["ir.model.data"].create({
            "module": "base",
            "name": "base_test_group",
            "model": "res.groups",
            "res_id": cls.test_group.id,
        })
        cls.definitions = cls.env['res.groups']._get_group_definitions()

    def parse_repr(self, group_repr):
        """ Return the group object from the string (given by the repr of the group object).

        :param group_repr: str
            Use | (union) and & (intersection) separator like the python object.
                intersection it's apply before union.
                Can use an invertion with ~.
        """
        if not group_repr:
            return self.definitions.universe
        res = None
        for union in group_repr.split('|'):
            union = union.strip()
            intersection = None
            if union.startswith('(') and union.endswith(')'):
                union = union[1:-1]
            for xmlid in union.split('&'):
                xmlid = xmlid.strip()
                leaf = ~self.definitions.parse(xmlid[1:]) if xmlid.startswith('~') else self.definitions.parse(xmlid)
                if intersection is None:
                    intersection = leaf
                else:
                    intersection &= leaf
            if intersection is None:
                return self.definitions.universe
            elif res is None:
                res = intersection
            else:
                res |= intersection
        return self.definitions.empty if res is None else res

    def test_groups_1_base(self):
        parse = self.definitions.parse

        self.assertEqual(str(parse('base.group_user') & parse('base.group_user')), "'base.group_user'")
        self.assertEqual(str(parse('base.group_user') & parse('base.group_system')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_system') & parse('base.group_user')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_erp_manager') & parse('base.group_system')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_system') & parse('base.group_multi_currency')), "'base.group_system' & 'base.group_multi_currency'")
        self.assertEqual(str(parse('base.group_user') | parse('base.group_user')), "'base.group_user'")
        self.assertEqual(str(parse('base.group_user') | parse('base.group_system')), "'base.group_user'")
        self.assertEqual(str(parse('base.group_system') | parse('base.group_public')), "'base.group_system' | 'base.group_public'")
        self.assertEqual(parse('base.group_system') < parse('base.group_erp_manager'), True)
        self.assertEqual(parse('base.group_system') < parse('base.group_sanitize_override'), True)
        self.assertEqual(parse('base.group_erp_manager') < parse('base.group_user'), True)
        self.assertEqual(parse('!base.group_portal') < parse('!base.group_public'), False)
        self.assertEqual(parse('base.base_test_group') == parse('base.base_test_group'), True)
        self.assertEqual(parse('base.group_system') <= parse('base.group_system'), True)
        self.assertEqual(parse('base.group_public') <= parse('base.group_system'), False)  # None ?
        self.assertEqual(parse('base.group_user') <= parse('base.group_system'), False)
        self.assertEqual(parse('base.group_system') <= parse('base.group_user'), True)
        self.assertEqual(parse('base.group_user') <= parse('base.group_portal'), False)
        self.assertEqual(parse('!base.group_portal') <= parse('!base.group_public'), False)

    def test_groups_2_from_commat_separator(self):
        parse = self.definitions.parse

        self.assertEqual(str(parse('base.group_user,base.group_system') & parse('base.group_system')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_user,base.group_erp_manager') & parse('base.group_system')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_user,base.group_portal') & parse('base.group_portal')), "'base.group_portal'")
        self.assertEqual(str(parse('base.group_user,base.group_portal,base.group_public,base.group_multi_company') & parse('base.group_portal,base.group_public')), "'base.group_portal' | 'base.group_public'")
        self.assertEqual(str(parse('base.group_system,base.base_test_group') & parse('base.group_user')), "'base.group_system' | 'base.base_test_group'")
        self.assertEqual(str(parse('base.group_system,base.group_portal') & parse('base.group_user')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_user') & parse('!base.group_portal,base.group_system')), "'base.group_system'")
        self.assertEqual(str(parse('!base.group_portal') & parse('base.group_portal,base.group_system')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_portal,!base.group_user') & parse('base.group_user')), "~*")
        self.assertEqual(str(parse('!base.group_user') & parse('base.group_portal,base.group_user')), "'base.group_portal'")
        self.assertEqual(str(parse('base.group_user') & parse('base.group_portal,!base.group_user')), "~*")
        self.assertEqual(str(parse('!base.group_user') & parse('base.group_portal,!base.group_system')), "'base.group_portal'")
        self.assertEqual(str(parse('!base.group_user,base.group_multi_currency') & parse('base.group_multi_currency,!base.group_system')), "~'base.group_user' & 'base.group_multi_currency'")
        self.assertEqual(str(parse('!base.group_user,base.group_portal') & parse('base.group_portal,!base.group_system')), "'base.group_portal'")
        self.assertEqual(str(parse('!*') & parse('base.group_portal')), "~*")
        self.assertEqual(str(parse('*') & parse('base.group_portal')), "'base.group_portal'")
        self.assertEqual(str(parse('base.group_user,!base.group_system') & parse('base.group_erp_manager,base.group_portal')), "'base.group_erp_manager' & ~'base.group_system'")
        self.assertEqual(str(parse('base.group_user,!base.group_system') & parse('base.group_portal,base.group_erp_manager')), "'base.group_erp_manager' & ~'base.group_system'")
        self.assertEqual(str(parse('base.group_user') & parse('base.group_portal,base.group_erp_manager,!base.group_system')), "'base.group_erp_manager' & ~'base.group_system'")
        self.assertEqual(str(parse('base.group_user') & parse('base.group_portal,base.group_system')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_user,base.group_system') & parse('base.group_portal,base.group_system')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_user') & parse('base.group_portal,base.group_erp_manager')), "'base.group_erp_manager'")
        self.assertEqual(str(parse('base.group_user') & parse('base.group_portal,!base.group_system')), "~*")
        self.assertEqual(str(parse('base.group_user,base.group_system') & parse('base.group_system,base.group_portal')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_user') & parse('base.group_system,base.group_portal')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_user,base.group_system') & parse('base.group_multi_currency')), "'base.group_user' & 'base.group_multi_currency'")
        self.assertEqual(str(parse('base.group_user,base.group_erp_manager') | parse('base.group_system')), "'base.group_user'")
        self.assertEqual(str(parse('base.group_user') | parse('base.group_portal,base.group_system')), "'base.group_user' | 'base.group_portal'")
        self.assertEqual(str(parse('!*') | parse('base.group_user')), "'base.group_user'")
        self.assertEqual(str(parse('base.group_user') | parse('!*')), "'base.group_user'")
        self.assertEqual(str(parse('!*') | parse('base.group_user,base.group_portal')), "'base.group_user' | 'base.group_portal'")
        self.assertEqual(str(parse('*') | parse('base.group_user')), "*")
        self.assertEqual(str(parse('base.group_user') | parse('*')), "*")
        self.assertEqual(str(parse('base.group_user,base.group_erp_manager') | parse('base.group_system,base.group_public')), "'base.group_user' | 'base.group_public'")
        self.assertEqual(parse('base.group_system') < parse('base.group_erp_manager,base.group_sanitize_override'), True)
        self.assertEqual(parse('!base.group_public,!base.group_portal') < parse('!base.group_public'), True)
        self.assertEqual(parse('base.group_system,base.base_test_group') == parse('base.group_system,base.base_test_group'), True)
        self.assertEqual(parse('base.group_system,base.base_test_group') == parse('base.base_test_group,base.group_system'), True)
        self.assertEqual(parse('base.group_system,base.base_test_group') == parse('base.base_test_group,base.group_public'), False)
        self.assertEqual(parse('base.group_system,base.base_test_group') == parse('base.base_test_group'), False)
        self.assertEqual(parse('base.group_user') <= parse('base.group_system,base.group_public'), False)
        self.assertEqual(parse('base.group_system') <= parse('base.group_user,base.group_public'), True)
        self.assertEqual(parse('base.group_public') <= parse('base.group_system,base.group_public'), True)
        self.assertEqual(parse('base.group_system,base.group_public') <= parse('base.group_system,base.group_public'), True)
        self.assertEqual(parse('base.group_system,base.group_public') <= parse('base.group_user,base.group_public'), True)
        self.assertEqual(parse('base.group_system,!base.group_public') <= parse('base.group_system'), True)
        self.assertEqual(parse('base.group_system,!base.group_multi_currency') <= parse('base.group_system'), True)
        self.assertEqual(parse('base.group_system') <= parse('base.group_system,!base.group_multi_currency'), False)
        self.assertEqual(parse('base.group_system') <= parse('base.group_system,!base.group_public'), True)
        self.assertEqual(parse('base.group_system') == parse('base.group_system,!base.group_public'), True)
        self.assertEqual(parse('!base.group_public,!base.group_portal') <= parse('!base.group_public'), True)
        self.assertEqual(parse('base.group_user,!base.group_multi_currency') <= parse('base.group_user,!base.group_system,!base.group_multi_currency'), False)
        self.assertEqual(parse('base.group_system,!base.group_portal,!base.group_public') <= parse('base.group_system,!base.group_public'), True)

    def test_groups_3_from_ref(self):
        parse = self.parse_repr

        self.assertEqual(str(parse('base.group_user & base.group_portal | base.group_user & ~base.group_system') & parse('base.group_public')), "~*")
        self.assertEqual(str(parse('base.group_user & base.group_portal | base.group_user & ~base.group_system') & parse('~base.group_user')), "~*")
        self.assertEqual(str(parse('base.group_user & base.group_portal | base.group_user & ~base.group_system') & parse('~base.group_user & base.group_portal')), "~*")
        self.assertEqual(str(parse('base.group_user & base.group_portal | base.group_user & base.group_system') & parse('base.group_user & ~base.group_portal')), "'base.group_system'")
        self.assertEqual(str(parse('base.group_public & base.group_erp_manager | base.group_public & base.group_portal') & parse('*')), "~*")
        self.assertEqual(str(parse('base.group_system & base.group_multi_currency') & parse('base.group_portal | base.group_system')), "'base.group_system' & 'base.group_multi_currency'")
        self.assertEqual(str(parse('base.group_portal & base.group_erp_manager') | parse('base.group_erp_manager')), "'base.group_erp_manager'")
        self.assertEqual(parse('base.group_system & base.group_multi_currency') < parse('base.group_system'), True)
        self.assertEqual(parse('base.base_test_group') == parse('base.base_test_group & base.group_user'), True)
        self.assertEqual(parse('base.group_system | base.base_test_group') == parse('base.group_system & base.group_user | base.base_test_group & base.group_user'), True)
        self.assertEqual(parse('base.group_public & base.group_multi_currency') <= parse('base.group_public'), True)
        self.assertEqual(parse('base.group_public') <= parse('base.group_public & base.group_multi_currency'), False)
        self.assertEqual(parse('base.group_public & base.group_user') <= parse('base.group_portal'), True)
        self.assertEqual(parse('base.group_public & base.group_user') <= parse('base.group_public | base.group_user'), True)
        self.assertEqual(parse('base.group_public & base.group_system') <= parse('base.group_user'), True)
        self.assertEqual(parse('base.group_public & base.group_system') <= parse('base.group_portal | base.group_user'), True)
        self.assertEqual(parse('base.group_public & base.group_multi_currency') <= parse('~base.group_public'), False)
        self.assertEqual(parse('base.group_portal & base.group_public | base.group_system & base.group_public') <= parse('base.group_public'), True)
        self.assertEqual(parse('base.group_portal & base.group_user | base.group_system & base.group_user') <= parse('base.group_user'), True)
        self.assertEqual(parse('base.group_portal & base.group_system | base.group_user & base.group_system') <= parse('base.group_system'), True)
        self.assertEqual(parse('base.group_portal & base.group_user | base.group_user & base.group_user') <= parse('base.group_user'), True)
        self.assertEqual(parse('base.group_portal & base.group_user | base.group_user & base.group_user') <= parse('base.group_user'), True)
        self.assertEqual(parse('base.group_public') <= parse('base.group_portal & base.group_public | base.group_system & base.group_public'), False)
        self.assertEqual(parse('base.group_user & base.group_multi_currency') <= parse('base.group_user & base.group_system & base.group_multi_currency'), False)
        self.assertEqual(parse('base.group_system & base.group_multi_currency') <= parse('base.group_user & base.group_system & base.group_multi_currency'), True)
        self.assertEqual(parse('base.group_system & base.group_multi_currency') <= parse('base.group_system'), True)
        self.assertEqual(parse('base.group_public') >= parse('base.group_portal & base.group_public | base.group_system & base.group_public'), True)
        self.assertEqual(parse('base.group_user & base.group_public') >= parse('base.group_user & base.group_portal & base.group_public | base.group_user & base.group_system & base.group_public'), True)
        self.assertEqual(parse('base.group_system & base.group_multi_currency') >= parse('base.group_system'), False)
        self.assertEqual(parse('base.group_system & base.group_multi_currency') > parse('base.group_system'), False)

    def test_groups_4_full_empty(self):
        user_group_ids = self.env.user._get_group_ids()
        self.assertFalse(self.definitions.parse('base.group_public').matches(user_group_ids))
        self.assertTrue(self.definitions.parse('*').matches(user_group_ids))
        self.assertFalse((~self.definitions.parse('*')).matches(user_group_ids))

    def test_groups_5_contains_user(self):
        # user is included into the defined group of users

        user = self.env['res.users'].create({
            'name': 'A User',
            'login': 'a_user',
            'email': 'a@user.com',
        })

        tests = [
            # group on the user, # groups access, access
            ('base.group_public', 'base.group_system | base.group_public', True),
            ('base.group_public,base.group_multi_currency', 'base.group_user | base.group_public', True),
            ('base.group_public', 'base.group_system & base.group_public', False),
            ('base.group_public', 'base.group_system | base.group_portal', False),
            ('base.group_public', 'base.group_system & base.group_portal', False),
            ('base.group_system', 'base.group_system | base.group_public', True),
            ('base.group_system', 'base.group_system & base.group_public', False),
            ('base.group_system', 'base.group_user | base.group_system', True),
            ('base.group_system', 'base.group_user & base.group_system', True),
            ('base.group_public', 'base.group_user | base.group_system', False),
            ('base.group_public', 'base.group_user & base.group_system', False),
            ('base.group_system', 'base.group_system & ~base.group_user', False),
            ('base.group_portal', 'base.group_system & ~base.group_user', False),
            ('base.group_user', 'base.group_user & ~base.group_system', True),
            ('base.group_user', '~base.group_system & base.group_user', True),
            ('base.group_system', 'base.group_user & ~base.group_system', False),
            ('base.group_portal', 'base.group_portal & ~base.group_user', True),
            ('base.group_system', '~base.group_system & base.group_user', False),
            ('base.group_system', '~base.group_system & ~base.group_user', False),
            ('base.group_user', 'base.group_user & base.group_sanitize_override & base.group_multi_currency', False),
            ('base.group_system', 'base.group_user & base.group_sanitize_override & base.group_multi_currency', False),
            ('base.group_system,base.group_multi_currency', 'base.group_user & base.group_sanitize_override & base.group_multi_currency', True),
            ('base.group_user,base.group_sanitize_override,base.group_multi_currency', 'base.group_user & base.group_sanitize_override & base.group_multi_currency', True),
            ('base.group_user', 'base.group_erp_manager | base.group_multi_company', False),
            ('base.group_user,base.group_erp_manager', 'base.group_erp_manager | base.group_multi_company', True),
        ]
        for user_groups, groups, result in tests:
            user.group_ids = [(6, 0, [self.env.ref(xmlid).id for xmlid in user_groups.split(',')])]
            self.assertEqual(self.parse_repr(groups).matches(user._get_group_ids()), result, f'User ({user_groups!r}) should {"" if result else "not "}have access to groups: ({groups!r})')

    def test_groups_6_distinct(self):
        user = self.env['res.users'].create({
            'name': 'A User',
            'login': 'a_user',
            'email': 'a@user.com',
            'group_ids': self.env.ref('base.group_user').ids,
        })

        # update res.users groups with distinct groups
        with self.assertRaises(ValidationError, msg="The user cannot have more than one user types."):
            user.group_ids = [(4, self.env.ref('base.group_public').id)]
        with self.assertRaises(ValidationError, msg="The user cannot have more than one user types."):
            user.group_ids = [(4, self.env.ref('base.group_portal').id)]

        user.group_ids = self.env.ref('base.group_user') + self.test_group

        self.assertEqual(set(self.test_group.all_implied_ids.get_external_id().values()), {'base.base_test_group', 'base.group_user', 'base.group_no_one', 'base.group_everyone'})

        # update res.group implied_ids having the effect that users have distinct groups
        with self.assertRaises(ValidationError, msg="The user cannot have more than one user types."):
            self.test_group.implied_ids += self.env.ref('base.group_public')

        self.assertEqual(set(self.test_group.all_implied_ids.get_external_id().values()), {'base.base_test_group', 'base.group_user', 'base.group_no_one', 'base.group_everyone'})

        with self.assertRaises(ValidationError, msg="The user cannot have more than one user types."):
            self.env.ref('base.group_public').implied_by_ids = self.test_group

        self.assertEqual(set(self.env.ref('base.group_public').implied_by_ids.get_external_id().values()), set())

        with self.assertRaises(ValidationError, msg="This makes a group imply two disjoint groups."):
            self.env.ref('base.group_public').implied_ids += self.test_group

        self.assertEqual(set(self.env.ref('base.group_public').all_implied_ids.get_external_id().values()), {'base.group_public', 'base.group_everyone'})

        new_group = self.env['res.groups'].create({
            'name': 'test group',
        })
        self.env["ir.model.data"].create({
            "module": "base",
            "name": "new_group",
            "model": "res.groups",
            "res_id": new_group.id,
        })
        self.env.ref('base.group_public').implied_ids += new_group
        self.assertEqual(set(self.env.ref('base.group_public').all_implied_ids.get_external_id().values()), {'base.group_public', 'base.new_group', 'base.group_everyone'})

    def test_groups_7_distinct(self):
        def create(name, implied_by_ids=[]):
            group = self.env['res.groups'].create({
                'name': f'test group {name}',
                'implied_by_ids': [g.id for g in implied_by_ids],
            })
            self.env["ir.model.data"].create({
                "module": "base",
                "name": f"test_group_{name}",
                "model": "res.groups",
                "res_id": group.id,
            })
            return group

        #       A
        #         \
        #  [B]      C
        #  / \     / \
        # D   E*  F   G*
        #
        a = create('a')
        b = create('b')
        c = create('c', [a])
        create('d', [b])
        e = self.env.ref('base.group_public')
        e.implied_by_ids = b
        create('f', [c])
        g = self.env.ref('base.group_user')
        g.implied_by_ids = c

        #       A
        #    /     \
        #  [B]      C
        #  / \     / \
        # D   E*  F   G*
        #
        with self.assertRaises(ValidationError, msg="This makes a group imply two disjoint groups."):
            b.implied_by_ids += a

        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'a_user',
            'email': 'a@user.com',
        })
        user.group_ids = a

        with self.assertRaises(ValidationError, msg=f"User 'A User' cannot be at the same time in exclusive groups {e.name!r}, {g.name!r}"):
            user.group_ids += b

        #       A
        #
        #  [B]      C
        #  / \     / \
        # D   E*  F   G*
        #
        a.implied_ids = self.env['res.groups']
        user.group_ids += b
        with self.assertRaises(ValidationError, msg=f"User 'A User' cannot be at the same time in exclusive groups {e.name!r}, {g.name!r}"):
            a.implied_ids += c

        #       A
        #         \
        #  [B]      C
        #  / \     / \
        # D   E*  F   G*
        #
        with self.assertRaises(ValidationError, msg=f"User 'A User' cannot be at the same time in exclusive groups {e.name!r}, {g.name!r}"):
            user.group_ids += c
