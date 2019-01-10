# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import common, TransactionCase


class Feedback(TransactionCase):
    def setUp(self):
        super().setUp()

        self.group0 = self.env['res.groups'].create({'name': "Group 0"})
        self.group1 = self.env['res.groups'].create({'name': "Group 1"})
        self.user = self.env['res.users'].create({
            'login': 'bob',
            'name': "Bob Bobman",
            'groups_id': [(4, self.env.ref('base.group_no_one').id)]
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
