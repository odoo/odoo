from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged, HttpCase, TransactionCase


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

Contact your administrator to request access if necessary.""",
        )

    def test_one_group(self):
        with self.assertRaises(AccessError) as ctx:
            self.env(user=self.user)['test_access_right.some_obj'].create({
                'val': 1,
            })
        self.assertEqual(
            ctx.exception.args[0],
            """You are not allowed to create 'Object For Test Access Right' (test_access_right.some_obj) records.

This operation is allowed for the following groups:\n\t- Group 0

Contact your administrator to request access if necessary.""",
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


@tagged('-at_install', 'post_install')
class TestAccess(HttpCase):
    def setUp(self):
        super().setUp()

        self.portal_user = self.env['res.users'].create({
            'login': 'P',
            'name': 'P',
            'group_ids': [Command.set([self.env.ref('base.group_portal').id])],
        })
        # a partner that can't be read by the portal user, would typically be a user's
        self.internal_user_partner = self.env['res.partner'].create({'name': 'I'})

        self.document = self.env['test_access_right.ticket'].create({
            'name': 'Need help here',
            'message_partner_ids': [Command.set([self.portal_user.partner_id.id,
                                            self.internal_user_partner.id])],
        })

    def test_check_access(self):
        """Typically, a document consulted by a portal user P
           will point to other records that P cannot read.
           For example, if P wants to consult a ticket of his,
           the ticket will have a reviewer or assigned user that is internal,
           and which partner cannot be read by P.
           This should not block P from accessing the ticket.
        """
        document = self.document.with_user(self.portal_user)
        # at this point, some fields might already be loaded in cache.
        # if so, it means we would bypass the ACL when trying to read the field
        # while this is bad, this is not the object of this test
        self.internal_user_partner.invalidate_model(['active'])
        # from portal's _document_check_access:
        document.check_access('read')
        # no raise, because we are supposed to be able to read our ticket

    def test_name_search_with_sudo(self):
        """Check that _name_search return correct values with sudo
        """
        no_access_user = self.env['res.users'].create({
            'login': 'no_access',
            'name': 'no_access',
            'group_ids': [Command.clear()],
        })
        document = self.env['test_access_right.ticket'].with_user(no_access_user)
        res = document.sudo().name_search('Need help here')
        self.assertEqual(res[0][1], "Need help here")
