import contextlib

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged, TransactionCase
from odoo.tools import mute_logger


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
class TestIRRuleFeedback(Feedback):
    """ Tests that proper feedback is returned on ir.rule errors
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'user_ids': [Command.link(cls.user.id)]})
        cls.model = cls.env['ir.model'].search([('model', '=', 'test_access_right.some_obj')])
        cls.record = cls.env['test_access_right.some_obj'].create({
            'val': 0,
        }).with_user(cls.user)
        cls.maxDiff = None

    def _make_rule(self, name, domain, global_=False, attr='write'):
        return self.env['ir.rule'].create({
            'name': name,
            'model_id': self.model.id,
            'groups': [] if global_ else [Command.link(self.group2.id)],
            'domain_force': domain,
            'perm_read': False,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
            'perm_' + attr: True,
        })

    def test_local(self):
        self._make_rule('rule 0', '[("val", "=", 42)]')
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description} ({self.record._name})

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )
        # debug mode
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

        ChildModel = self.env['test_access_right.inherits']
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            ChildModel.with_user(self.user).create({'some_id': self.record.id, 'val': 2})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_locals(self):
        self._make_rule('rule 0', '[("val", "=", 42)]')
        self._make_rule('rule 1', '[("val", "=", 78)]')
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0
- rule 1

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_globals_all(self):
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[("val", "=", 78)]', global_=True)
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0
- rule 1

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_globals_any(self):
        """ Global rules are AND-eded together, so when access fails it
        might be just one of the rules, and we want an exact listing
        """
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_combination(self):
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        self._make_rule('rule 2', '[(0, "=", 1)]')
        self._make_rule('rule 3', '[("val", "=", 55)]')
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0
- rule 2
- rule 3

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_warn_company_no_access(self):
        """ If one of the failing rules mentions company_id, add a note that
        this might be a multi-company issue, but the user doesn't access to this company
        then no information about the company is shown.
        """
        self._make_rule('rule 0', "[('company_id', '=', user.company_id.id)]")
        self._make_rule('rule 1', '[("val", "=", 0)]', global_=True)
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'write' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_warn_company_no_company_field(self):
        """ If one of the failing rules mentions company_id, add a note that
        this might be a multi-company issue, but the record doesn't have company_id field
        then no information about the company is shown.
        """
        ChildModel = self.env['test_access_right.child'].sudo()
        self.env['ir.rule'].create({
            'name': 'rule 0',
            'model_id': self.env['ir.model'].search([('model', '=', ChildModel._name)]).id,
            'groups': [],
            'domain_force': '[("parent_id.company_id", "=", user.company_id.id)]',
            'perm_read': True,
        })
        self.record.sudo().company_id = self.env['res.company'].create({'name': 'Brosse Inc.'})
        self.user.sudo().company_ids = [Command.link(self.record.company_id.id)]
        child_record = ChildModel.create({'parent_id': self.record.id}).with_user(self.user)
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            _ = child_record.parent_id
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'read' access to:
- {child_record._description}, {child_record.display_name} ({child_record._name}: {child_record.id})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.""",
        )

    def test_warn_company_access(self):
        """ because of prefetching, read() goes through a different codepath
        to apply rules
        """
        self.record.sudo().company_id = self.env['res.company'].create({'name': 'Brosse Inc.'})
        self.user.sudo().company_ids = [Command.link(self.record.company_id.id)]
        self._make_rule('rule 0', "[('company_id', '=', user.company_id.id)]", attr='read')
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            _ = self.record.val
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'read' access to:
- {self.record._description}, {self.record.display_name} ({self.record._name}: {self.record.id}, company={self.record.sudo().company_id.display_name})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.

This seems to be a multi-company issue, you might be able to access the record by switching to the company: {self.record.sudo().company_id.display_name}.""",
        )
        p = self.env['test_access_right.inherits'].create({'some_id': self.record.id})
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertRaisesRegex(
            AccessError,
            r"Implicitly accessed through 'Object for testing related access rights' \(test_access_right.inherits\)\.",
        ):
            p.with_user(self.user).val

    def test_warn_company_access_multi_record(self):
        """ Test that AccessError handle correctly several companies """
        company_1, company_2 = self.env['res.company'].create([
            {'name': 'Brosse Inc.'},
            {'name': 'Brosse Inc. 2'},
        ])
        records = self.env["test_access_right.some_obj"].create([
            {"val": 1, "company_id": company_1.id},
            {"val": 2, "company_id": company_2.id},
        ])
        record_1, record_2 = records
        self.user.sudo().company_ids = [Command.link(company_1.id), Command.link(company_2.id)]
        self._make_rule('rule 0', "[('company_id', '=', False)]", attr='read')
        self.env.invalidate_all()
        with self.debug_mode(), self.assertRaises(AccessError) as ctx:
            _ = records.with_user(self.user).read(["val"])
        self.assertEqual(
            ctx.exception.args[0],
            f"""Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, {self.user.name} (id={self.user.id}) doesn't have 'read' access to:
- {record_1._description}, {record_1.display_name} ({record_1._name}: {record_1.id}, company={record_1.company_id.display_name})
- {record_2._description}, {record_2.display_name} ({record_2._name}: {record_2.id}, company={record_2.company_id.display_name})

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.

Note: this might be a multi-company issue. Switching company may help - in Odoo, not in real life!""")


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ObjCateg = cls.env['test_access_right.obj_categ']
        SomeObj = cls.env['test_access_right.some_obj']
        cls.categ = ObjCateg.create({'name': 'Food'})
        cls.allowed = SomeObj.create({'val': 1, 'categ_id': cls.categ.id})
        cls.forbidden = SomeObj.create({'val': -1, 'categ_id': cls.categ.id})
        # create a global rule forbidding access to records with a negative
        # (or zero) val
        cls.env['ir.rule'].create({
            'name': 'Forbid negatives',
            'model_id': cls.env.ref('test_base.model_test_access_right_some_obj').id,
            'domain_force': "[('val', '>', 0)]",
        })
        # create a global rule that forbid access to records without
        # categories, the search is part of the test
        cls.env['ir.rule'].create({
            'name': 'See all categories',
            'model_id': cls.env.ref('test_base.model_test_access_right_some_obj').id,
            'domain_force': "[('categ_id', 'in', user.env['test_access_right.obj_categ'].search([]).ids)]",
        })

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_basic_access(self):
        env = self.env(user=self.env.ref('base.public_user'))
        allowed = self.allowed.with_env(env)
        forbidden = self.forbidden.with_env(env)

        # this one should not blow up
        self.assertEqual(allowed.val, 1)

        # but this one should
        allowed.invalidate_model(['val'])
        with self.assertRaises(AccessError):
            self.assertEqual(forbidden.val, -1)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_group_rule(self):
        env = self.env(user=self.env.ref('base.public_user'))
        allowed = self.allowed.with_env(env)
        forbidden = self.forbidden.with_env(env)

        # we forbid access to the public group, to which the public user belongs
        self.env['ir.rule'].create({
            'name': 'Forbid public group',
            'model_id': self.env.ref('test_base.model_test_access_right_some_obj').id,
            'groups': [Command.set([self.env.ref('base.group_public').id])],
            'domain_force': "[(0, '=', 1)]",
        })

        # everything should blow up
        (allowed + forbidden).invalidate_model(['val'])
        with self.assertRaises(AccessError):
            self.assertEqual(forbidden.val, -1)
        with self.assertRaises(AccessError):
            self.assertEqual(allowed.val, 1)

    def test_many2many(self):
        """ Test assignment of many2many field where rules apply. """
        ids = [self.allowed.id, self.forbidden.id]

        # create container as superuser, connected to all some_objs
        container_admin = self.env['test_access_right.container'].create({'some_ids': [Command.set(ids)]})
        self.assertItemsEqual(container_admin.some_ids.ids, ids)

        # check the container as the public user
        container_user = container_admin.with_user(self.env.ref('base.public_user'))
        container_user.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [self.allowed.id])

        # this should fail
        with self.assertRaises(AccessError):
            container_user.write({'some_ids': [Command.set(ids)]})

        container_admin.write({'some_ids': [Command.set(ids)]})
        container_user.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [self.allowed.id])
        container_admin.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_admin.some_ids.ids, ids)

        # this removes all records
        container_user.write({'some_ids': [Command.clear()]})
        container_user.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [])
        container_admin.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_admin.some_ids.ids, [])

    def test_access_rule_performance(self):
        env = self.env(user=self.env.ref('base.public_user'))
        Model = env['test_access_right.some_obj']
        # cache warmup for check() in 'ir.model.access'
        Model.check_access('read')
        with self.assertQueryCount(0):
            Model._filtered_access('read')

    def test_no_context_in_ir_rules(self):
        """ The context should not impact the ir rules. """
        ObjCateg = self.env['test_access_right.obj_categ']
        SomeObj = self.env['test_access_right.some_obj']

        # validate the effect of context on category search, there are
        # no existing media category
        self.assertTrue(ObjCateg.search([]))
        self.assertFalse(ObjCateg.with_context(only_media=True).search([]))

        # record1 is food and is accessible with an empy context
        self.env.registry.clear_cache()
        records = SomeObj.search([('id', '=', self.allowed.id)])
        self.assertTrue(records)

        # it should also be accessible as the context is not used when
        # searching for SomeObjs
        self.env.registry.clear_cache()
        records = SomeObj.with_context(only_media=True).search([('id', '=', self.allowed.id)])
        self.assertTrue(records)

    def test_check_access_rule_with_inherits(self):
        """
        For models in `_inherits`, verify that both methods `check_access`
        and `_search` check the rules from parent models.
        """
        ChildModel = self.env['test_access_right.inherits']
        allowed_child, __ = children = ChildModel.create([
            {'some_id': self.allowed.id}, {'some_id': self.forbidden.id},
        ])

        user = self.env.ref('base.public_user')
        search_result = children.with_user(user).search([('id', 'in', children.ids)], order='id')
        filter_result = children.with_user(user)._filtered_access('read')

        self.assertEqual(search_result, allowed_child)
        self.assertEqual(filter_result, allowed_child)

    def test_flush_with_inherits(self):
        """
        For models with `_inherits`, verify that fields of the rules from inherited models
        are flushed correctly.
        """
        ChildModel = self.env['test_access_right.inherits']
        child = ChildModel.create([{'some_id': self.allowed.id}])
        self.env.flush_all()

        self.env['ir.rule'].create({
            'name': 'Forbid 0 value',
            'model_id': self.env['ir.model']._get('test_access_right.some_obj').id,
            'domain_force': str([('val', '!=', 0)]),
        })

        user = self.env.ref('base.public_user')

        # the parent record is accessible, so is the child record
        search_result = ChildModel.with_user(user).search([('id', '=', child.id)], order='id')
        self.assertEqual(search_result, child)

        # make the parent record inaccessible, and verify that the child record
        # becomes inaccessible, too
        self.allowed.val = 0
        search_result = ChildModel.with_user(user).search([('id', '=', child.id)], order='id')
        self.assertEqual(search_result, ChildModel)

    def test_domain_constrains(self):
        """ An error should be raised if domain is not correct """

        rule = self.env['ir.rule'].create({
            'name': 'Test record rule',
            'model_id': self.env.ref('test_base.model_test_access_right_some_obj').id,
            'domain_force': [],
        })
        invalid_domains = [
            'A really bad domain!',
            [(1, '!=', 1)],
            [('non_existing_field', '=', 'value')],
        ]

        for domain in invalid_domains:
            with self.assertRaisesRegex(ValidationError, 'Invalid domain'):
                rule.domain_force = domain

        valid_domains = [
            False,
            [(1, '=', 1)],
            [('val', '=', 12)],
        ]
        for domain in valid_domains:
            # no error is raised
            rule.domain_force = domain

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_ir_rule_cache_after_error(self):
        NB_RECORD = 14  # At least twice 6, 6 is used by _make_access_error
        # copy the forbidden record 15 times
        SomeObj = self.env['test_access_right.some_obj']
        forbiddens = SomeObj.create([{'val': -1, 'categ_id': self.categ.id}] * NB_RECORD)
        forbiddens.invalidate_model()

        env = self.env(user=self.env.ref('base.public_user'))
        forbiddens = forbiddens.with_env(env)
        forbiddens.browse().check_access('read')

        # Don't use assertRaise since it invalidates the cache
        # and it is what we want to test.
        with contextlib.suppress(AccessError):
            forbiddens.check_access('read')
            self.fail('Previous line should raise AccessError')

        with contextlib.suppress(AccessError):
            forbiddens[0].val
            self.fail('Previous line should raise AccessError')

        with contextlib.suppress(AccessError):
            forbiddens[NB_RECORD - 1].val
            self.fail('Previous line should raise AccessError')
