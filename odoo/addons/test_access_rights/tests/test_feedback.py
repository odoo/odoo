# -*- coding: utf-8 -*-
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
            'groups_id': [(4, self.group2.id),]
        })


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

    def test_no_groups(self):
        """ Operation is never allowed
        """
        with self.assertRaises(AccessError) as ctx:
            self.record.sudo(self.user).write({'val': 10})
        self.assertEqual(
            ctx.exception.args[0],
            """Sorry, you are not allowed to modify documents of type 'Object For Test Access Right' (test_access_right.some_obj). No group currently allows this operation."""
        )

    def test_one_group(self):
        with self.assertRaises(AccessError) as ctx:
            self.env(user=self.user)['test_access_right.some_obj'].create({
                'val': 1
            })
        self.assertEqual(
            ctx.exception.args[0],
            """Sorry, you are not allowed to create documents of type 'Object For Test Access Right' (test_access_right.some_obj). This operation is allowed for the groups:
	- Group 0"""
        )

    def test_two_groups(self):
        r = self.record.sudo(self.user)
        expected = """Sorry, you are not allowed to access documents of type 'Object For Test Access Right' (test_access_right.some_obj). This operation is allowed for the groups:
	- Group 0
	- Group 1"""
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
        }).sudo(self.user)

    def _make_rule(self, name, domain, global_=False, attr='write'):
        return self.env['ir.rule'].create({
            'name': name,
            'model_id': self.model.id,
            'groups': [] if global_ else [(4, self.group2.id)],
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
            'The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: "Object For Test Access Right" (test_access_right.some_obj), Operation: write)'
        )

        # debug mode
        self.env.ref('base.group_no_one').write({'users': [(4, self.user.id)]})
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation ("write" on "Object For Test Access Right" (test_access_right.some_obj)) was rejected because of the following rules:
- rule 0

(records: [%s], uid: %d)""" % (self.record.id, self.user.id)
        )



        p = self.env['test_access_right.parent'].create({'obj_id': self.record.id})
        self.assertRaisesRegex(
            AccessError,
            r"Implicitly accessed through \\'Object for testing related access rights\\' \(test_access_right.parent\)\.",
            p.sudo(self.user).write, {'val': 1}
        )

    def test_locals(self):
        self.env.ref('base.group_no_one').write(
            {'users': [(4, self.user.id)]})
        self._make_rule('rule 0', '[("val", "=", 42)]')
        self._make_rule('rule 1', '[("val", "=", 78)]')
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation ("write" on "Object For Test Access Right" (test_access_right.some_obj)) was rejected because of the following rules:
- rule 0
- rule 1

(records: [%s], uid: %d)""" % (self.record.id, self.user.id)
        )

    def test_globals_all(self):
        self.env.ref('base.group_no_one').write(
            {'users': [(4, self.user.id)]})
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[("val", "=", 78)]', global_=True)
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation ("write" on "Object For Test Access Right" (test_access_right.some_obj)) was rejected because of the following rules:
- rule 0
- rule 1

(records: [%s], uid: %d)""" % (self.record.id, self.user.id)
        )

    def test_globals_any(self):
        """ Global rules are AND-eded together, so when an access fails it
        might be just one of the rules, and we want an exact listing
        """
        self.env.ref('base.group_no_one').write(
            {'users': [(4, self.user.id)]})
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation ("write" on "Object For Test Access Right" (test_access_right.some_obj)) was rejected because of the following rules:
- rule 0

(records: [%s], uid: %d)""" % (self.record.id, self.user.id)
        )

    def test_combination(self):
        self.env.ref('base.group_no_one').write(
            {'users': [(4, self.user.id)]})
        self._make_rule('rule 0', '[("val", "=", 42)]', global_=True)
        self._make_rule('rule 1', '[(1, "=", 1)]', global_=True)
        self._make_rule('rule 2', '[(0, "=", 1)]')
        self._make_rule('rule 3', '[("val", "=", 55)]')
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation ("write" on "Object For Test Access Right" (test_access_right.some_obj)) was rejected because of the following rules:
- rule 0
- rule 2
- rule 3

(records: [%s], uid: %d)""" % (self.record.id, self.user.id)
        )

    def test_warn_company(self):
        """ If one of the failing rules mentions company_id, add a note that
        this might be a multi-company issue.
        """
        self.env.ref('base.group_no_one').write(
            {'users': [(4, self.user.id)]})
        self._make_rule('rule 0', "[('company_id', 'child_of', user.company_id.id)]")
        self._make_rule('rule 1', '[("val", "=", 0)]', global_=True)
        with self.assertRaises(AccessError) as ctx:
            self.record.write({'val': 1})
        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation ("write" on "Object For Test Access Right" (test_access_right.some_obj)) was rejected because of the following rules:
- rule 0

Note: this might be a multi-company issue.

(records: [%s], uid: %d)""" % (self.record.id, self.user.id)
        )

    def test_read(self):
        """ because of prefetching, read() goes through a different codepath
        to apply rules
        """
        self.env.ref('base.group_no_one').write(
            {'users': [(4, self.user.id)]})
        self._make_rule('rule 0', "[('company_id', 'child_of', user.company_id.id)]", attr='read')
        self._make_rule('rule 1', '[("val", "=", 1)]', global_=True, attr='read')
        with self.assertRaises(AccessError) as ctx:
            _ = self.record.val
        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation ("read" on "Object For Test Access Right" (test_access_right.some_obj)) was rejected because of the following rules:
- rule 0
- rule 1

Note: this might be a multi-company issue.

(records: [%s], uid: %d)""" % (self.record.id, self.user.id)
        )

        p = self.env['test_access_right.parent'].create({'obj_id': self.record.id})
        # p.sudo(self.user).val
        self.assertRaisesRegex(
            AccessError,
            r"Implicitly accessed through \\'Object for testing related access rights\\' \(test_access_right.parent\)\.",
            lambda: p.sudo(self.user).val
        )

class TestFieldGroupFeedback(Feedback):

    def setUp(self):
        super().setUp()
        self.record = self.env['test_access_right.some_obj'].create({
            'val': 0,
        }).sudo(self.user)


    def test_read(self):
        self.env.ref('base.group_no_one').write(
            {'users': [(4, self.user.id)]})
        with self.assertRaises(AccessError) as ctx:
            _ = self.record.forbidden

        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation can not be completed due to security restrictions.

Document type: Object For Test Access Right (test_access_right.some_obj)
Operation: read
Fields:
- forbidden (allowed for groups 'User types / Internal User', 'Test Group'; forbidden for groups 'Extra Rights / Technical Features', 'User types / Public')"""
        )

    def test_write(self):
        self.env.ref('base.group_no_one').write(
            {'users': [(4, self.user.id)]})

        with self.assertRaises(AccessError) as ctx:
            self.record.write({'forbidden': 1, 'forbidden2': 2})

        self.assertEqual(
            ctx.exception.args[0],
            """The requested operation can not be completed due to security restrictions.

Document type: Object For Test Access Right (test_access_right.some_obj)
Operation: write
Fields:
- forbidden (allowed for groups 'User types / Internal User', 'Test Group'; forbidden for groups 'Extra Rights / Technical Features', 'User types / Public')
- forbidden2 (allowed for groups 'Test Group')"""
        )
