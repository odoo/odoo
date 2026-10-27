# -*- coding: utf-8 -*-
from unittest.mock import Mock

import odoo
from odoo import SUPERUSER_ID, Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase
from odoo.tools.misc import mute_logger


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
            'groups_id': [Command.set([cls.group2.id, cls.env.ref('base.group_user').id])],
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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ACL = cls.env['ir.model.access']
        m = cls.env['ir.model'].search([('model', '=', 'test_access_right.some_obj')])
        ACL.search([('model_id', '=', m.id)]).unlink()
        ACL.create({
            'name': "read",
            'model_id': m.id,
            'group_id': cls.group1.id,
            'perm_read': True,
        })
        ACL.create({
            'name':  "create-and-read",
            'model_id': m.id,
            'group_id': cls.group0.id,
            'perm_read': True,
            'perm_create': True,
        })
        cls.record = cls.env['test_access_right.some_obj'].create({'val': 5})
        # values are in cache, clear them up for the test
        cls.env.flush_all()
        cls.env.invalidate_all()

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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'users': [Command.link(cls.user.id)]})
        cls.model = cls.env['ir.model'].search([('model', '=', 'test_access_right.some_obj')])
        cls.record = cls.env['test_access_right.some_obj'].create({
            'val': 0,
        }).with_user(cls.user)

    def debug_mode(self):
        odoo.http._request_stack.push(Mock(db=self.env.cr.dbname, env=self.env, debug=True))
        self.addCleanup(odoo.http._request_stack.pop)
        self.env.flush_all()
        self.env.invalidate_all()

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
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'write' access to:
- %s (%s)

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record._name))
        # debug mode
        self.debug_mode()
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'write' access to:
- %s, %s (%s: %s)

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record.display_name, self.record._name, self.record.id))

        ChildModel = self.env['test_access_right.inherits']
        with self.assertRaises(AccessError) as ctx:
            ChildModel.with_user(self.user).create({'some_id': self.record.id, 'val': 2})
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'write' access to:
- %s, %s (%s: %s)

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record.display_name, self.record._name, self.record.id))

    def test_locals(self):
        self._make_rule('rule 0', '[("val", "=", 42)]')
        self._make_rule('rule 1', '[("val", "=", 78)]')
        self.debug_mode()
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'write' access to:
- %s, %s (%s: %s)

Blame the following rules:
- rule 0
- rule 1

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record.display_name, self.record._name, self.record.id))

    def test_globals_all(self):
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[("val", "=", 78)]', global_=True)
        self.debug_mode()
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'write' access to:
- %s, %s (%s: %s)

Blame the following rules:
- rule 0
- rule 1

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record.display_name, self.record._name, self.record.id))

    def test_globals_any(self):
        """ Global rules are AND-eded together, so when an access fails it
        might be just one of the rules, and we want an exact listing
        """
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        self.debug_mode()
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'write' access to:
- %s, %s (%s: %s)

Blame the following rules:
- rule 0

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record.display_name, self.record._name, self.record.id))

    def test_combination(self):
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        self._make_rule('rule 2', '[(0, "=", 1)]')
        self._make_rule('rule 3', '[("val", "=", 55)]')
        self.debug_mode()
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'write' access to:
- %s, %s (%s: %s)

Blame the following rules:
- rule 0
- rule 2
- rule 3

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record.display_name, self.record._name, self.record.id))

    def test_warn_company_no_access(self):
        """ If one of the failing rules mentions company_id, add a note that
        this might be a multi-company issue, but the user doesn't access to this company
        then no information about the company is showed.
        """
        self._make_rule('rule 0', "[('company_id', '=', user.company_id.id)]")
        self._make_rule('rule 1', '[("val", "=", 0)]', global_=True)
        self.debug_mode()
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'write' access to:
- %s, %s (%s: %s)

Blame the following rules:
- rule 0

Note: this might be a multi-company issue. Switching company may help - in Odoo, not in real life!

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record.display_name, self.record._name, self.record.id))

    def test_warn_company_no_company_field(self):
        """ If one of the failing rules mentions company_id, add a note that
        this might be a multi-company issue, but the record doesn't have company_id field
        then no information about the company is showed.
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
        self.debug_mode()
        with self.assertRaises(AccessError) as ctx:
            _ = child_record.parent_id
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'read' access to:
- %s, %s (%s: %s)

Blame the following rules:
- rule 0

Note: this might be a multi-company issue. Switching company may help - in Odoo, not in real life!

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, child_record._description, child_record.display_name, child_record._name, child_record.id))

    def test_warn_company_access(self):
        """ because of prefetching, read() goes through a different codepath
        to apply rules
        """
        self.record.sudo().company_id = self.env['res.company'].create({'name': 'Brosse Inc.'})
        self.user.sudo().company_ids = [Command.link(self.record.company_id.id)]
        self._make_rule('rule 0', "[('company_id', '=', user.company_id.id)]", attr='read')
        self.debug_mode()
        with self.assertRaises(AccessError) as ctx:
            _ = self.record.val
        self.assertEqual(
            ctx.exception.args[0],
            """Uh-oh! Looks like you have stumbled upon some top-secret records.

Sorry, %s (id=%s) doesn't have 'read' access to:
- %s, %s (%s: %s, company=%s)

Blame the following rules:
- rule 0

Note: this might be a multi-company issue. Switching company may help - in Odoo, not in real life!

If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies."""
        % (self.user.name, self.user.id, self.record._description, self.record.display_name, self.record._name, self.record.id, self.record.sudo().company_id.display_name))
        p = self.env['test_access_right.inherits'].create({'some_id': self.record.id})
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertRaisesRegex(
            AccessError,
            r"Implicitly accessed through 'Object for testing related access rights' \(test_access_right.inherits\)\.",
        ):
            p.with_user(self.user).val

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
- forbidden (allowed for groups 'Test Group'; forbidden for groups 'Extra Rights / Technical Features', 'User types / Public')"""
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

    @mute_logger('odoo.models')
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
- forbidden (allowed for groups 'Test Group'; forbidden for groups 'Extra Rights / Technical Features', 'User types / Public')
- forbidden2 (allowed for groups 'Test Group')"""
    % self.user.id
        )

    @mute_logger('odoo.models')
    def test_check_field_access_rights_domain(self):
        with self.assertRaises(AccessError):
            self.record.search([('forbidden3', '=like', 'blu%')])

        with self.assertRaises(AccessError):
            self.record.search([('parent_id.forbidden3', '=like', 'blu%')])

        with self.assertRaises(AccessError):
            self.record.search([('parent_id', 'any', [('forbidden3', '=like', 'blu%')])])

        with self.assertRaises(AccessError):
            self.inherits_record.search([('forbidden3', '=like', 'blu%')])

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
            self.record._read_group([('forbidden3', '=like', 'blu%')], ['val'])

        with self.assertRaises(AccessError):
            self.record._read_group([('parent_id.forbidden3', '=like', 'blu%')], ['val'])

        with self.assertRaises(AccessError):
            self.record._read_group([], ['forbidden3'])

        with self.assertRaises(AccessError):
            self.record._read_group([], [], ['forbidden3:array_agg'])
