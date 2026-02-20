from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged, TransactionCase
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
            'group_ids': [Command.set([cls.group2.id, cls.env.ref('base.group_user').id])],
        })


@tagged('at_install', '-post_install')  # LEGACY at_install
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
