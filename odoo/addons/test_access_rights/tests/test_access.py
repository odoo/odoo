from contextlib import contextmanager
import re

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestAccess(TransactionCase):
    MODEL = 'test_access_right.some_obj'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group1 = cls.env['res.groups'].create({'name': "Group 1"})
        cls.group2 = cls.env['res.groups'].create({'name': "Group 2"})
        cls.group3 = cls.env['res.groups'].create({'name': "Group 3"})

        # user belongs to Group 1, Group 2, but not to Group 3
        groups = cls.env.ref('base.group_user') + cls.group1 + cls.group2
        cls.user = cls.env['res.users'].create({
            'login': 'bob',
            'name': "Bob Bobman",
            'group_ids': [Command.set(groups.ids)],
        })

        # discard all existing access on model
        cls.env['ir.access'].search([('model_id', '=', cls.MODEL)]).unlink()

        # create records: Mario, Luigi, Peach, Toad, Yoshi, Bowser
        cls.records = cls.env[cls.MODEL].create([{}] * 6).with_user(cls.user)
        cls.mario, cls.luigi, cls.peach, cls.toad, cls.yoshi, cls.bowser = cls.records
        cls.model = cls.records.browse()

    def make_access(self, name="", records=None, group=None, operation='r', **kwargs):
        """ Create some access on records (or all records if None) """
        return self.env['ir.access'].create({
            'name': name,
            'model_id': self.env['ir.model']._get_id(self.MODEL),
            'group_id': group.id if group else False,
            'operation': operation,
            'domain': str([('id', 'in', records.ids)]) if records else False,
            **kwargs,
        })

    def assertAccess(self, allowed, operation='read'):
        self.assertTrue(self.model.has_access(operation))
        self.model.check_access(operation)

        for record in self.records:
            if record in allowed:
                self.assertTrue(record.has_access(operation))
                record.check_access(operation)
            else:
                self.assertFalse(record.has_access(operation))
                with self.assertAccessError():
                    record.check_access(operation)

        allowed.check_access(operation)

        if self.records - allowed:
            with self.assertAccessError():
                self.records.check_access(operation)

        self.assertEqual(self.records._filtered_access(operation), allowed)

    @contextmanager
    def assertAccessError(self, message=None):
        with mute_logger('odoo.addons.base.models.ir_access'):
            if message:
                with self.assertRaisesRegex(AccessError, re.compile(message, re.S)):
                    yield
            else:
                with self.assertRaises(AccessError):
                    yield

    def test_for_fields(self):
        access = self.make_access(self.records, operation='rw')
        self.assertTrue(access.for_read)
        self.assertTrue(access.for_write)
        self.assertFalse(access.for_create)
        self.assertFalse(access.for_unlink)

    def test_operation_and_for_fields(self):
        access = self.make_access(
            self.records, operation='rw', for_read=True, for_write=False, for_create=True,
        )
        self.assertTrue(access.for_read)
        self.assertFalse(access.for_write)
        self.assertTrue(access.for_create)
        self.assertFalse(access.for_unlink)
        self.assertEqual(access.operation, 'rc')

    def test_sudo(self):
        records = self.records.sudo()

        self.assertTrue(records.has_access('read'))
        self.assertTrue(records.has_access('write'))
        self.assertTrue(records.has_access('create'))
        self.assertTrue(records.has_access('unlink'))

        self.assertEqual(records._filtered_access('read'), records)
        self.assertEqual(records._filtered_access('write'), records)
        self.assertEqual(records._filtered_access('create'), records)
        self.assertEqual(records._filtered_access('unlink'), records)

        records.check_access('read')
        records.check_access('write')
        records.check_access('create')
        records.check_access('unlink')

    def test_no_access(self):
        self.assertFalse(self.records.has_access('read'))
        self.assertFalse(self.records.has_access('write'))
        self.assertFalse(self.records.has_access('create'))
        self.assertFalse(self.records.has_access('unlink'))

        self.assertFalse(self.records._filtered_access('read'))
        self.assertFalse(self.records._filtered_access('write'))
        self.assertFalse(self.records._filtered_access('create'))
        self.assertFalse(self.records._filtered_access('unlink'))

        with self.assertAccessError():
            self.records.check_access('read')
        with self.assertAccessError():
            self.records.check_access('write')
        with self.assertAccessError():
            self.records.check_access('create')
        with self.assertAccessError():
            self.records.check_access('unlink')

    def test_no_permission_one_restriction(self):
        self.make_access(records=self.records)

        self.assertFalse(self.model.has_access('read'))
        self.assertFalse(self.model.has_access('write'))

        self.assertFalse(self.records._filtered_access('read'))
        self.assertFalse(self.records._filtered_access('write'))

        with self.assertAccessError():
            self.model.check_access('read')
        with self.assertAccessError():
            self.model.check_access('write')
        with self.assertAccessError():
            self.records.check_access('read')

    def test_one_permission(self):
        # read access, write access on humans
        humans = self.mario + self.luigi + self.peach
        self.make_access(group=self.group1, operation='r')
        self.make_access(records=humans, group=self.group1, operation='w')

        self.assertAccess(self.records, 'read')
        self.assertAccess(humans, 'write')

    def test_two_permissions_in_group(self):
        self.make_access(records=self.mario + self.luigi, group=self.group1)
        self.make_access(records=self.mario + self.peach, group=self.group1)

        # union of permissions
        self.assertAccess(self.mario + self.luigi + self.peach)

    def test_two_permissions_in_distinct_groups(self):
        self.make_access(records=self.mario + self.luigi, group=self.group1)
        self.make_access(records=self.mario + self.peach, group=self.group2)
        self.make_access(records=self.mario + self.yoshi, group=self.group3)

        # union of permissions
        self.assertAccess(self.mario + self.luigi + self.peach)

    def test_one_permission_one_restriction(self):
        self.make_access(records=self.mario + self.peach + self.bowser, group=self.group1)
        self.make_access(records=self.records - self.bowser)

        # union of permissions, intersection of restrictions
        self.assertAccess(self.mario + self.peach)

    def test_two_permissions_one_restriction(self):
        self.make_access(records=self.mario + self.luigi + self.bowser, group=self.group1)
        self.make_access(records=self.mario + self.peach + self.bowser, group=self.group2)
        self.make_access(records=self.records - self.bowser)

        # union of permissions, intersection of restrictions
        self.assertAccess(self.mario + self.luigi + self.peach)

    def test_two_permissions_two_restrictions(self):
        self.make_access(records=self.mario + self.luigi + self.bowser, group=self.group1)
        self.make_access(records=self.mario + self.peach + self.bowser, group=self.group2)
        self.make_access(records=self.records - self.bowser)
        self.make_access(records=self.records - self.peach)

        # union of permissions, intersection of restrictions
        self.assertAccess(self.mario + self.luigi)

    def test_special_user_manager(self):
        # one partial permission, one full permission
        self.make_access(records=self.mario + self.luigi + self.bowser, group=self.group1)
        self.make_access(group=self.group2)
        # one restriction
        self.make_access(records=self.records - self.bowser)

        self.assertAccess(self.records - self.bowser)

    def test_special_restrict_operations(self):
        # full permission on all operations
        self.make_access(group=self.group1, operation='r')
        self.make_access(group=self.group2, operation='rwcd')
        # restriction on some operations
        self.make_access(records=self.records - self.bowser, operation='wcd')

        self.assertAccess(self.records, operation='read')
        self.assertAccess(self.records - self.bowser, operation='write')
        self.assertAccess(self.records - self.bowser, operation='create')
        self.assertAccess(self.records - self.bowser, operation='unlink')

    def test_error_message_no_access(self):
        self.make_access(group=self.group3, operation='cd')

        # read, write: no access at all
        with self.assertAccessError(r"You are not allowed to access.*No group currently allows this operation"):
            self.records.check_access('read')
        with self.assertAccessError(r"You are not allowed to modify.*No group currently allows this operation"):
            self.records.check_access('write')

        # create, unlink: access in Group 3
        with self.assertAccessError(
            r"You are not allowed to create.*"
            r"This operation is allowed for the following groups:\s*- Group 3"
        ):
            self.records.check_access('create')
        with self.assertAccessError(
            r"You are not allowed to delete.*"
            r"This operation is allowed for the following groups:\s*- Group 3"
        ):
            self.records.check_access('unlink')

    def test_error_message_partial_access(self):
        humans = self.records[:3]
        self.make_access("Restrict to humans", records=humans, group=self.group1)

        self.assertEqual(self.records._filtered_access('read'), humans)

        with self.assertAccessError(
            r"Uh-oh.*"
            rf"Sorry, Bob Bobman \(id={self.user.id}\) doesn't have 'read' access to:\s*"
            r"- Object For Test Access Right \(test_access_right\.some_obj\)\s*"
            r"If you really"
        ):
            self.records.check_access('read')

        with self.debug_mode():
            with self.assertAccessError(
                r"Uh-oh.*"
                rf"Sorry, Bob Bobman \(id={self.user.id}\) doesn't have 'read' access to:\s*"
                rf"- Object For Test Access Right, {self.toad.display_name}.*"
                rf"- Object For Test Access Right, {self.yoshi.display_name}.*"
                rf"- Object For Test Access Right, {self.bowser.display_name}.*"
                r"Blame the following accesses:\s*"
                r"- Restrict to humans\s*"
                r"If you really"
            ):
                self.records.check_access('read')

    def test_error_message_restricted_access(self):
        humans = self.records[:3]
        self.make_access("See all", group=self.group1)
        self.make_access("Restrict to humans", records=humans)

        self.assertEqual(self.records._filtered_access('read'), humans)

        with self.assertAccessError(
            r"Uh-oh.*"
            rf"Sorry, Bob Bobman \(id={self.user.id}\) doesn't have 'read' access to:\s*"
            r"- Object For Test Access Right \(test_access_right\.some_obj\)\s*"
            r"If you really"
        ):
            self.records.check_access('read')

        with self.debug_mode():
            with self.assertAccessError(
                r"Uh-oh.*"
                rf"Sorry, Bob Bobman \(id={self.user.id}\) doesn't have 'read' access to:\s*"
                rf"- Object For Test Access Right, {self.toad.display_name}.*"
                rf"- Object For Test Access Right, {self.yoshi.display_name}.*"
                rf"- Object For Test Access Right, {self.bowser.display_name}.*"
                r"Blame the following accesses:\s*"
                r"- Restrict to humans\s*"
                r"If you really"
            ):
                self.records.check_access('read')

    def test_error_message_partial_and_restricted_access(self):
        humans = self.records[:3]
        self.make_access("See good guys", records=self.records[:5], group=self.group1)
        self.make_access("Restrict to humans", records=humans)

        self.assertEqual(self.records._filtered_access('read'), humans)

        with self.assertAccessError(
            r"Uh-oh.*"
            rf"Sorry, Bob Bobman \(id={self.user.id}\) doesn't have 'read' access to:\s*"
            r"- Object For Test Access Right \(test_access_right\.some_obj\)\s*"
            r"If you really"
        ):
            self.records.check_access('read')

        with self.debug_mode():
            with self.assertAccessError(
                r"Uh-oh.*"
                rf"Sorry, Bob Bobman \(id={self.user.id}\) doesn't have 'read' access to:\s*"
                rf"- Object For Test Access Right, {self.toad.display_name}.*"
                rf"- Object For Test Access Right, {self.yoshi.display_name}.*"
                rf"- Object For Test Access Right, {self.bowser.display_name}.*"
                r"Blame the following accesses:\s*"
                r"- See good guys\s*"
                r"- Restrict to humans\s*"
                r"If you really"
            ):
                self.records.check_access('read')
