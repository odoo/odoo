from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import common

from odoo.addons.base.models.res_groups import ResGroups


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

    def test_prevent_inherited_views_in_group_assignment(self):
        """ Groups can only be assigned non-inherited (primary) views.

        Inherited views (mode='extension') must not be linked to groups directly.
        They inherit access from their parent view. Attempting to assign an
        inherited view to a group should raise a ValidationError. """

        View = self.env['ir.ui.view']
        group = self.test_group
        normal_view = View.create({
            'name': 'Test View',
            'type': 'form',
            'model': 'res.partner',
            'arch': '<form><field name="name"/></form>',
        })
        inherited_view = View.create({
            'name': 'Inherited View',
            'type': 'form',
            'model': 'res.partner',
            'inherit_id': normal_view.id,
            'mode': 'extension',
            'arch': '''
                <xpath expr="//field[@name='name']" position="after">
                    <field name="email"/>
                </xpath>
            ''',
        })

        # Case 1: inherited view should fail
        with self.assertRaises(ValidationError):
            group.write({
                'view_access': [Command.link(inherited_view.id)],
            })

        # Case 2: normal view should pass
        group.write({
            'view_access': [Command.link(normal_view.id)],
        })
        self.assertIn(normal_view, group.view_access)

        # Case 3: both views should fail
        with self.assertRaises(ValidationError):
            group.write({
                'view_access': [
                    Command.link(normal_view.id),
                    Command.link(inherited_view.id)
                ],
            })

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

        self.assertEqual(set(self.test_group.all_implied_ids.get_external_id().values()), {'base.base_test_group', 'base.group_user', 'base.group_user_regular', 'base.group_no_one', 'base.group_everyone'})

        # update res.group implied_ids having the effect that users have distinct groups
        with self.assertRaises(ValidationError, msg="The user cannot have more than one user types."):
            self.test_group.implied_ids += self.env.ref('base.group_public')

        self.assertEqual(set(self.test_group.all_implied_ids.get_external_id().values()), {'base.base_test_group', 'base.group_user', 'base.group_user_regular', 'base.group_no_one', 'base.group_everyone'})

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
        self.assertEqual(set(self.env.ref('base.group_public').all_implied_ids.get_external_id().values()), {'base.group_public', 'base.new_group', 'base.group_user_regular', 'base.group_everyone'})

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

    def test_groups_7_multi_external_id(self):
        system = self.env.ref('base.group_system')
        self.env['ir.model.data']._update_xmlids([{'xml_id': 'base.test_group_system', 'record': system}])
        self.assertGreater(len(system._get_external_ids()[system.id]), 1, "Group with multiple xmlids")
        self.definitions = self.env['res.groups']._get_group_definitions()
        self.assertEqual(self.parse_repr('base.group_system'), self.parse_repr('base.test_group_system'))

    def test_reduce_to_light_groups(self):
        job = self.env['res.groups.privilege'].create({'name': 'Monkey Job Positions'})
        accounting = self.env['res.groups.privilege'].create({'name': 'Monkey Accounting'})
        fleet = self.env['res.groups.privilege'].create({'name': 'Monkey Feet'})
        project = self.env['res.groups.privilege'].create({'name': 'Monkey Project'})
        hr = self.env['res.groups.privilege'].create({'name': 'Monkey Hr'})

        user = self.env.ref('base.group_user')

        export = self.env['res.groups'].create({'name': 'Monk Export'})

        hr_interviewer = self.env['res.groups'].create({'name': 'HR Interviewer', 'privilege_id': hr.id})
        hr_interviewer.implied_ids += user
        hr_user = self.env['res.groups'].create({'name': 'HR Officer', 'privilege_id': hr.id})
        hr_user.implied_ids += hr_interviewer
        hr_manager = self.env['res.groups'].create({'name': 'HR Manager', 'privilege_id': hr.id})
        hr_manager.implied_ids += hr_user

        proj_user = self.env['res.groups'].create({'name': 'Project User', 'privilege_id': project.id})
        proj_user.implied_ids += user
        proj_manager = self.env['res.groups'].create({'name': 'Project Manager', 'privilege_id': project.id})
        proj_manager.implied_ids += proj_user + export

        fleet_user = self.env['res.groups'].create({'name': 'Fleet User', 'privilege_id': fleet.id})
        fleet_user.implied_ids += user
        fleet_manager = self.env['res.groups'].create({'name': 'Fleet Manager', 'privilege_id': fleet.id})
        fleet_manager.implied_ids += fleet_user

        acc_ext = self.env['res.groups'].create({'name': 'Accounting Extern', 'privilege_id': accounting.id})
        acc_ext.implied_ids += user
        acc_user = self.env['res.groups'].create({'name': 'Accounting User', 'privilege_id': accounting.id})
        acc_user.implied_ids += user
        acc_manager = self.env['res.groups'].create({'name': 'Accounting Manager', 'privilege_id': accounting.id})
        acc_manager.implied_ids += acc_user + export

        team_leader = self.env['res.groups'].create({'name': 'Team leader', 'privilege_id': job.id})
        team_leader.implied_ids += proj_manager + hr_interviewer
        office_manager = self.env['res.groups'].create({'name': 'Office Manager', 'privilege_id': job.id})
        office_manager.implied_ids += acc_user + fleet_user
        cto = self.env['res.groups'].create({'name': 'cto'})
        cto.implied_ids += acc_manager + fleet_manager + proj_manager + hr_manager

        null = self.env['res.groups']

        light_groups = ('base.group_user', hr_interviewer.id, fleet_user.id, acc_user.id, acc_ext.id)

        def test_reduce_to_light(a, b):
            with patch.object(ResGroups, '_get_light_group_xmlids', lambda s: light_groups):
                self.assertEqual(a._reduce_to_light_groups().mapped('name'), b.mapped('name'), f"Try to reduce: {a.mapped('name')}")

        # hr
        test_reduce_to_light(hr_interviewer, hr_interviewer)
        test_reduce_to_light(hr_user, hr_interviewer)
        test_reduce_to_light(hr_manager, hr_interviewer)

        # project
        test_reduce_to_light(proj_user, null)
        test_reduce_to_light(proj_manager, null)

        # fleet
        test_reduce_to_light(fleet_user, fleet_user)
        test_reduce_to_light(fleet_manager, fleet_user)

        # accounting
        test_reduce_to_light(acc_ext, acc_ext)
        test_reduce_to_light(acc_user, acc_user)
        test_reduce_to_light(acc_manager, acc_user)

        # job positions
        test_reduce_to_light(team_leader, null)
        test_reduce_to_light(office_manager, null)
        test_reduce_to_light(cto, null)

        # combine
        test_reduce_to_light(cto + acc_manager, acc_user)
        test_reduce_to_light(cto + acc_ext, acc_ext)
        test_reduce_to_light(team_leader + proj_manager, null)
        test_reduce_to_light(team_leader + hr_interviewer, hr_interviewer)
        test_reduce_to_light(proj_manager + fleet_manager + hr_manager, fleet_user + hr_interviewer)
        test_reduce_to_light(hr_manager + user, user + hr_interviewer)

    def _assert_regular_user_consistency(self):
        """ Invariant enforced by ``_apply_group_regular``: every regular
        (non-light) group must transitively imply ``base.group_user_regular``.

        If this does not hold, the database is inconsistent: ``_compute_role``
        classifies a user from its *direct* groups (``_is_light_groups``) while
        ``_search_role`` relies on the *transitive* presence of the regular-user
        marker. A regular group not implying the marker would let a user own
        that group's rights while being seen as a light user (and be invisible
        to the ``role = regular_user`` filter).
        """
        Groups = self.env['res.groups']
        regular = self.env.ref('base.group_user_regular')
        light_groups = Groups.browse([
            group.id
            for xid in Groups._get_light_group_xmlids()
            if (group := self.env.ref(xid, raise_if_not_found=False))
        ])
        excluded = light_groups | regular | Groups._get_user_type_groups()
        for group in Groups.search([]):
            if group in excluded:
                continue
            self.assertIn(
                regular, group.all_implied_ids,
                f"The regular group {group.name!r} must imply the regular-user marker",
            )

    def test_regular_user_applied_on_create(self):
        """ The regular-user marker is granted automatically when groups are
        created, so that DB data cannot end up with a regular group that does
        not flag its users as regular. """
        regular = self.env.ref('base.group_user_regular')
        group_user = self.env.ref('base.group_user')  # light group

        hr = self.env['res.groups.privilege'].create({'name': 'Monkey Hr'})
        hr_interviewer = self.env['res.groups'].create({'name': 'HR Interviewer', 'privilege_id': hr.id})
        hr_interviewer.implied_ids += group_user
        hr_user = self.env['res.groups'].create({'name': 'HR Officer', 'privilege_id': hr.id})
        hr_user.implied_ids += hr_interviewer
        hr_manager = self.env['res.groups'].create({'name': 'HR Manager', 'privilege_id': hr.id})
        hr_manager.implied_ids += hr_user

        # a group without privilege is a regular group on its own
        export = self.env['res.groups'].create({'name': 'Monk Export'})

        # the lowest group of a privilege carries the marker directly
        self.assertIn(regular, hr_interviewer.implied_ids)
        # the highest group only carries it transitively (through the lowest one),
        # it is not redundantly flagged as a direct regular group
        self.assertNotIn(regular, hr_manager.implied_ids)
        self.assertIn(regular, hr_manager.all_implied_ids)
        # a group without privilege carries the marker directly
        self.assertIn(regular, export.implied_ids)
        # a light group is never turned into a (direct) regular group
        self.assertNotIn(group_user, regular.implied_by_ids)

        self._assert_regular_user_consistency()

    def test_regular_user_applied_on_write(self):
        """ Editing the group topology re-applies the regular-user marker, so a
        group promoted/demoted in a privilege stays consistent. """
        regular = self.env.ref('base.group_user_regular')
        group_user = self.env.ref('base.group_user')  # light group

        hr = self.env['res.groups.privilege'].create({'name': 'Monkey Hr'})
        hr_interviewer = self.env['res.groups'].create({'name': 'HR Interviewer', 'privilege_id': hr.id})
        hr_interviewer.implied_ids += group_user
        hr_user = self.env['res.groups'].create({'name': 'HR Officer', 'privilege_id': hr.id})
        hr_user.implied_ids += hr_interviewer
        hr_manager = self.env['res.groups'].create({'name': 'HR Manager', 'privilege_id': hr.id})
        hr_manager.implied_ids += hr_user

        # baseline: the top group only implies the marker transitively
        self.assertIn(regular, hr_interviewer.implied_ids)
        self.assertNotIn(regular, hr_manager.implied_ids)

        # detach the manager from the chain: it becomes a lowest-level regular
        # group and the marker must be re-applied to it on write
        hr_manager.write({'implied_ids': [Command.unlink(hr_user.id), Command.link(group_user.id)]})
        self.assertIn(regular, hr_manager.implied_ids)
        self._assert_regular_user_consistency()

    def test_regular_user_applied_on_duplicate(self):
        """ Duplicating a manager group must not silently produce a group that
        grants regular rights while escaping the regular-user flag: the copy
        still implies the marker (transitively), so its users are detected as
        regular users. """
        regular = self.env.ref('base.group_user_regular')
        group_user = self.env.ref('base.group_user')  # light group

        hr = self.env['res.groups.privilege'].create({'name': 'Monkey Hr'})
        hr_interviewer = self.env['res.groups'].create({'name': 'HR Interviewer', 'privilege_id': hr.id})
        hr_interviewer.implied_ids += group_user
        hr_user = self.env['res.groups'].create({'name': 'HR Officer', 'privilege_id': hr.id})
        hr_user.implied_ids += hr_interviewer
        hr_manager = self.env['res.groups'].create({'name': 'HR Manager', 'privilege_id': hr.id})
        hr_manager.implied_ids += hr_user

        hr_manager_copy = hr_manager.copy()

        # the marker is not directly applied to the duplicated manager...
        self.assertNotIn(regular, hr_manager_copy.implied_ids)
        # ... but the copy is still a regular group transitively
        self.assertIn(regular, hr_manager_copy.all_implied_ids)
        self.assertFalse(hr_manager_copy._is_light_groups())

        # a user in the duplicated manager is correctly detected as a regular
        # user (both by _compute_role and _search_role, i.e. consistent data)
        user = self.env['res.users'].create({
            'name': 'Monkey Manager',
            'login': 'monkey_manager',
            'group_ids': [Command.set((group_user + hr_manager_copy).ids)],
        })
        self.assertEqual(user.role, 'regular_user')
        self.assertIn(regular, user.all_group_ids)
        self.assertIn(user, self.env['res.users'].search([('role', '=', 'regular_user')]))

        self._assert_regular_user_consistency()

    def test_regular_user_applied_on_unlink_intermediate(self):
        """ Deleting an intermediate group of an implication chain must not
        leave a regular group without the regular-user marker.

        Manager -> Leader -> User (marked regular). When the intermediate
        Leader is unlinked, Manager loses its path to the marker, so it must be
        re-applied (Manager becomes a lowest-level regular group and implies the
        marker directly). """
        regular = self.env.ref('base.group_user_regular')
        group_user = self.env.ref('base.group_user')  # light group

        priv = self.env['res.groups.privilege'].create({'name': 'Monkey Hr'})
        hr_user = self.env['res.groups'].create({'name': 'HR User', 'privilege_id': priv.id})
        hr_user.implied_ids += group_user
        hr_leader = self.env['res.groups'].create({'name': 'HR Leader', 'privilege_id': priv.id})
        hr_leader.implied_ids += hr_user
        hr_manager = self.env['res.groups'].create({'name': 'HR Manager', 'privilege_id': priv.id})
        hr_manager.implied_ids += hr_leader

        # baseline: Manager reaches the marker through the chain
        self.assertIn(regular, hr_manager.all_implied_ids)

        hr_leader.unlink()

        # the chain is broken, but Manager must still imply the marker
        self.assertNotIn(hr_leader, hr_manager.implied_ids)
        self.assertIn(regular, hr_manager.all_implied_ids)
        self._assert_regular_user_consistency()
