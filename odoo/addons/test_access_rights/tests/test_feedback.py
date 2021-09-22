# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, Command
from odoo.exceptions import AccessError
from odoo.tests import common, TransactionCase


class Feedback(TransactionCase):
    def setUp(self):
        super().setUp()

        self.group0 = self.env['res.groups'].create({'name': "Group 0"})
        self.group1 = self.env['res.groups'].create({'name': "Group 1"})
        self.group2 = self.env['res.groups'].create({'name': "Group 2"})
        self.user = self.env['res.users'].create({
            'login': 'bob',
            'name': "Bob Bobman",
            'groups_id': [Command.set(self.group2.ids)],
        })


class TestSudo(Feedback):
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
            'groups_id': [Command.set([self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
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


class TestACLFeedback(Feedback):
    """ Tests that proper feedback is returned on ir.model.access errors
    """
    def setUp(self):
        super().setUp()
        ACL = self.env['ir.model.access']
        m = self.env['ir.model'].search([('model', '=', 'test_access_right.some_obj')])
        ACL.search([('model_id', '=', m.id)]).unlink()
        ACL.create({
            'name': "read",
            'model_id': m.id,
            'group_id': self.group1.id,
            'perm_read': True,
        })
        ACL.create({
            'name':  "create-and-read",
            'model_id': m.id,
            'group_id': self.group0.id,
            'perm_read': True,
            'perm_create': True,
        })
        self.record = self.env['test_access_right.some_obj'].create({'val': 5})
        # values are in cache, clear them up for the test
        ACL.flush()
        ACL.invalidate_cache()

    def test_no_groups(self):
        """ Operation is never allowed
        """
        with self.assertRaises(AccessError) as ctx:
            self.record.with_user(self.user).write({'val': 10})
        self.assertEqual(
            ctx.exception.args[0],
            """You are not allowed to modify 'Object For Test Access Right' (test_access_right.some_obj) records.

No group currently allows this operation.

Contact your administrator to request access if necessary."""
        )

    def test_one_group(self):
        with self.assertRaises(AccessError) as ctx:
            self.env(user=self.user)['test_access_right.some_obj'].create({
                'val': 1
            })
        self.assertEqual(
            ctx.exception.args[0],
            """You are not allowed to create 'Object For Test Access Right' (test_access_right.some_obj) records.

This operation is allowed for the following groups:\n\t- Group 0

Contact your administrator to request access if necessary."""
        )

    def test_two_groups(self):
        r = self.record.with_user(self.user)
        expected = """You are not allowed to access 'Object For Test Access Right' (test_access_right.some_obj) records.

This operation is allowed for the following groups:\n\t- Group 0\n\t- Group 1

Contact your administrator to request access if necessary."""
        with self.assertRaises(AccessError) as ctx:
            # noinspection PyStatementEffect
            r.val
        self.assertEqual(ctx.exception.args[0], expected)
        with self.assertRaises(AccessError) as ctx:
            r.read(['val'])
        self.assertEqual(ctx.exception.args[0], expected)

class TestIRRuleFeedback(Feedback):
    """ Tests that proper feedback is returned on ir.rule errors
    """
    def setUp(self):
        super().setUp()
        self.model = self.env['ir.model'].search([('model', '=', 'test_access_right.some_obj')])
        self.record = self.env['test_access_right.some_obj'].create({
            'val': 0,
        }).with_user(self.user)

    def _make_rule(self, name, domain, global_=False, attr='write'):
        res = self.env['ir.rule'].create({
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
        return res

    def test_local(self):
        self._make_rule('rule 0', '[("val", "=", 42)]')
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Due to security restrictions, you are not allowed to modify 'Object For Test Access Right' (test_access_right.some_obj) records.

Contact your administrator to request access if necessary.""")

        # debug mode
        self.env.ref('base.group_no_one').write({'users': [Command.link(self.user.id)]})
        self.env.ref('base.group_user').write({'users': [Command.link(self.user.id)]})
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Due to security restrictions, you are not allowed to modify 'Object For Test Access Right' (test_access_right.some_obj) records.

Records: %s (id=%s)
User: %s (id=%s)

This restriction is due to the following rules:
- rule 0

Contact your administrator to request access if necessary.""" % (self.record.display_name, self.record.id, self.user.name, self.user.id)
        )



        p = self.env['test_access_right.parent'].create({'obj_id': self.record.id})
        with self.assertRaisesRegex(
            AccessError,
            r"Implicitly accessed through 'Object for testing related access rights' \(test_access_right.parent\)\.",
        ):
            p.with_user(self.user).write({'val': 1})

    def test_locals(self):
        self.env.ref('base.group_no_one').write({'users': [Command.link(self.user.id)]})
        self.env.ref('base.group_user').write({'users': [Command.link(self.user.id)]})
        self._make_rule('rule 0', '[("val", "=", 42)]')
        self._make_rule('rule 1', '[("val", "=", 78)]')
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Due to security restrictions, you are not allowed to modify 'Object For Test Access Right' (test_access_right.some_obj) records.

Records: %s (id=%s)
User: %s (id=%s)

This restriction is due to the following rules:
- rule 0
- rule 1

Contact your administrator to request access if necessary.""" % (self.record.display_name, self.record.id, self.user.name, self.user.id)
        )

    def test_globals_all(self):
        self.env.ref('base.group_no_one').write({'users': [Command.link(self.user.id)]})
        self.env.ref('base.group_user').write({'users': [Command.link(self.user.id)]})
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[("val", "=", 78)]', global_=True)
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Due to security restrictions, you are not allowed to modify 'Object For Test Access Right' (test_access_right.some_obj) records.

Records: %s (id=%s)
User: %s (id=%s)

This restriction is due to the following rules:
- rule 0
- rule 1

Contact your administrator to request access if necessary.""" % (self.record.display_name, self.record.id, self.user.name, self.user.id)
        )

    def test_globals_any(self):
        """ Global rules are AND-eded together, so when an access fails it
        might be just one of the rules, and we want an exact listing
        """
        self.env.ref('base.group_no_one').write({'users': [Command.link(self.user.id)]})
        self.env.ref('base.group_user').write({'users': [Command.link(self.user.id)]})
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Due to security restrictions, you are not allowed to modify 'Object For Test Access Right' (test_access_right.some_obj) records.

Records: %s (id=%s)
User: %s (id=%s)

This restriction is due to the following rules:
- rule 0

Contact your administrator to request access if necessary.""" % (self.record.display_name, self.record.id, self.user.name, self.user.id)
        )

    def test_combination(self):
        self.env.ref('base.group_no_one').write({'users': [Command.link(self.user.id)]})
        self.env.ref('base.group_user').write({'users': [Command.link(self.user.id)]})
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        self._make_rule('rule 2', '[(0, "=", 1)]')
        self._make_rule('rule 3', '[("val", "=", 55)]')
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Due to security restrictions, you are not allowed to modify 'Object For Test Access Right' (test_access_right.some_obj) records.

Records: %s (id=%s)
User: %s (id=%s)

This restriction is due to the following rules:
- rule 0
- rule 2
- rule 3

Contact your administrator to request access if necessary.""" % (self.record.display_name, self.record.id, self.user.name, self.user.id)
        )

    def test_warn_company(self):
        """ If one of the failing rules mentions company_id, add a note that
        this might be a multi-company issue.
        """
        self.env.ref('base.group_no_one').write({'users': [Command.link(self.user.id)]})
        self.env.ref('base.group_user').write({'users': [Command.link(self.user.id)]})
        self._make_rule('rule 0', "[('company_id', '=', user.company_id.id)]")
        self._make_rule('rule 1', '[("val", "=", 0)]', global_=True)
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Due to security restrictions, you are not allowed to modify 'Object For Test Access Right' (test_access_right.some_obj) records.

Records: %s (id=%s)
User: %s (id=%s)

This restriction is due to the following rules:
- rule 0

Note: this might be a multi-company issue.

Contact your administrator to request access if necessary.""" % (self.record.display_name, self.record.id, self.user.name, self.user.id)
        )

    def test_read(self):
        """ because of prefetching, read() goes through a different codepath
        to apply rules
        """
        self.env.ref('base.group_no_one').write({'users': [Command.link(self.user.id)]})
        self.env.ref('base.group_user').write({'users': [Command.link(self.user.id)]})
        self._make_rule('rule 0', "[('company_id', '=', user.company_id.id)]", attr='read')
        self._make_rule('rule 1', '[("val", "=", 1)]', global_=True, attr='read')
        with self.assertRaises(AccessError) as ctx:
            _ = self.record.val
        self.assertEqual(
            ctx.exception.args[0],
            """Due to security restrictions, you are not allowed to access 'Object For Test Access Right' (test_access_right.some_obj) records.

Records: %s (id=%s)
User: %s (id=%s)

This restriction is due to the following rules:
- rule 0
- rule 1

Note: this might be a multi-company issue.

Contact your administrator to request access if necessary.""" % (self.record.display_name, self.record.id, self.user.name, self.user.id)
        )

        p = self.env['test_access_right.parent'].create({'obj_id': self.record.id})
        p.flush()
        p.invalidate_cache()
        with self.assertRaisesRegex(
            AccessError,
            r"Implicitly accessed through 'Object for testing related access rights' \(test_access_right.parent\)\.",
        ):
            p.with_user(self.user).val

class TestFieldGroupFeedback(Feedback):

    def setUp(self):
        super().setUp()
        self.record = self.env['test_access_right.some_obj'].create({
            'val': 0,
        }).with_user(self.user)


    def test_read(self):
        self.env.ref('base.group_no_one').write(
            {'users': [Command.link(self.user.id)]})
        with self.assertRaises(AccessError) as ctx:
            _ = self.record.forbidden

        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation can not be completed due to security restrictions.

Document type: Object For Test Access Right (test_access_right.some_obj)
Operation: read
User: %s
Fields:
- forbidden (allowed for groups 'User types / Internal User', 'Test Group'; forbidden for groups 'Extra Rights / Technical Features', 'User types / Public')"""
    % self.user.id
        )

        with self.assertRaises(AccessError) as ctx:
            _ = self.record.forbidden3

        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation can not be completed due to security restrictions.

Document type: Object For Test Access Right (test_access_right.some_obj)
Operation: read
User: %s
Fields:
- forbidden3 (always forbidden)""" % self.user.id
        )

    def test_write(self):
        self.env.ref('base.group_no_one').write(
            {'users': [Command.link(self.user.id)]})

        with self.assertRaises(AccessError) as ctx:
            self.record.write({'forbidden': 1, 'forbidden2': 2})

        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation can not be completed due to security restrictions.

Document type: Object For Test Access Right (test_access_right.some_obj)
Operation: write
User: %s
Fields:
- forbidden (allowed for groups 'User types / Internal User', 'Test Group'; forbidden for groups 'Extra Rights / Technical Features', 'User types / Public')
- forbidden2 (allowed for groups 'Test Group')"""
    % self.user.id
        )
