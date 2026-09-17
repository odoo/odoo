import datetime
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import freeze_time, users
from odoo.tests.common import RecordCapturer
from odoo.tools import html2plaintext, mute_logger

from odoo.addons.document.tests.test_document_common import (
    TEXT,
    TransactionCaseDocuments,
)
from odoo.addons.mail.tests.common import MockEmail


class TestDocumentsAccess(TransactionCaseDocuments, MockEmail):
    def test_change_owner_matches_the_write_rule(self):
        document = self.env["document.document"].create(
            {
                "type": "binary",
                "name": "owned.txt",
                "datas": TEXT,
                "mimetype": "text/plain",
                "folder_id": self.folder_b.id,
                "owner_id": self.doc_user.id,
                "access_internal": "edit",
            }
        )

        document.with_user(self.document_manager).owner_id = self.internal_user
        self.assertEqual(document.owner_id, self.internal_user)

        document.with_user(self.doc_user).sudo().owner_id = self.doc_user
        self.assertEqual(document.owner_id, self.doc_user)

        document.sudo().owner_id = self.document_manager.id
        with self.assertRaises(AccessError):
            document.with_user(self.doc_user).owner_id = self.doc_user
        self.assertEqual(document.owner_id, self.document_manager)

    def test_noop_access_update_queues_no_tracking_work(self):
        """An update that changes nothing must not wake the tracking cron.

        The queue is drained by `ir_cron_documents_access_tracking`, which
        `_create_access_tracking` triggers. Triggering it for an update that
        produced no change wakes it to drain an empty queue, and `_trigger`
        does not de-duplicate, so every such call leaves its own row behind.
        """
        Tracking = self.env["document.access.tracking"]
        Trigger = self.env["ir.cron.trigger"]
        folder = self.folder_a

        # settle on a known value, then ask for the value it already has
        folder.action_update_access_rights(access_internal="view")
        self.env.flush_all()
        before = (Tracking.search_count([]), Trigger.search_count([]))

        folder.action_update_access_rights(access_internal="view")
        self.env.flush_all()
        self.assertEqual(
            (Tracking.search_count([]), Trigger.search_count([])),
            before,
            "a no-op update queued tracking work or woke the cron",
        )

        # ...and a real change still queues both, so the guard above cannot be
        # satisfied by simply not tracking anything any more.
        folder.action_update_access_rights(access_internal="edit")
        self.env.flush_all()
        self.assertGreater(
            Tracking.search_count([]), before[0], "a real change was not tracked"
        )
        self.assertGreater(
            Trigger.search_count([]), before[1], "the tracking cron was not woken"
        )

    def test_move_into_unreadable_non_folder_reports_invalid_folder(self):
        hidden = self.env["document.document"].create(
            {
                "type": "binary",
                "name": "hidden-secret-name.txt",
                "datas": TEXT,
                "mimetype": "text/plain",
                "owner_id": self.document_manager.id,
                "access_internal": "none",
                "access_via_link": "none",
            }
        )
        self._assert_raises_check_access_rule(hidden.with_user(self.doc_user), "read")

        with self.assertRaises(UserError) as capture:
            self.document_txt.with_user(self.doc_user).write({"folder_id": hidden.id})
        self.assertNotIsInstance(
            capture.exception, AccessError, "leaked that the target is unreadable"
        )
        self.assertNotIn("hidden-secret-name", str(capture.exception))

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule")
    def test_access_type_internal(self):
        self.assertEqual(self.folder_a.access_internal, "view")
        self._assert_no_members(self.folder_a)
        self.assertTrue(self.public_user._is_public())
        self.assertTrue(self.portal_user._is_portal())

        self._assert_raises_check_access_rule(self.folder_a.with_user(self.public_user))
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.portal_user))
        self.folder_a.with_user(self.internal_user).check_access("read")
        self._assert_raises_check_access_rule(
            self.folder_a.with_user(self.internal_user), "write"
        )

        self.folder_a.access_internal = "edit"
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.public_user))
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.portal_user))
        self.folder_a.with_user(self.internal_user).check_access("write")

        self.assertTrue(
            self.env["document.document"].search([("id", "=", self.folder_a.id)])
        )
        self.assertFalse(
            self.env["document.document"]
            .with_user(self.portal_user)
            .search([("id", "=", self.folder_a.id)])
        )

    def test_forbidden_partner_members(self):
        public_partner = self.env.ref("base.public_user").partner_id
        with self.assertRaises(
            ValidationError, msg="public user should not be a member"
        ):
            self.env["document.access"].create(
                {
                    "document_id": self.folder_a.id,
                    "partner_id": public_partner.id,
                    "role": "view",
                }
            )
        self.assertTrue(
            self.env["document.access"].create(
                {
                    "document_id": self.folder_a.id,
                    "partner_id": public_partner.id,
                    "last_access_date": fields.Datetime.now(),
                }
            )
        )
        regular_partner = self.env["res.partner"].create({"name": "Regular member"})
        self.assertTrue(
            self.env["document.access"].create(
                {
                    "document_id": self.folder_a.id,
                    "partner_id": regular_partner.id,
                    "role": "view",
                }
            )
        )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_access_from_documents_access(self):
        self.assertEqual(self.folder_a.access_internal, "view")
        self.assertEqual(self.folder_a.access_via_link, "none")
        self.assertEqual(self.folder_a_a.access_internal, "view")
        self.assertEqual(self.folder_a_a.access_via_link, "none")

        self._assert_no_members(self.folder_a)
        self.assertTrue(self.portal_user._is_portal())

        folder_a_as_portal = self.folder_a.with_user(self.portal_user)
        folder_a_a_as_portal = self.folder_a_a.with_user(self.portal_user)
        folder_a_as_internal = self.folder_a.with_user(self.internal_user)

        self._assert_raises_check_access_rule(folder_a_as_portal)
        self._assert_raises_check_access_rule(folder_a_a_as_portal)

        portal_access = self.env["document.access"].create(
            {
                "document_id": self.folder_a.id,
                "partner_id": self.portal_user.partner_id.id,
                "role": "view",
            }
        )
        folder_a_as_internal.check_access("read")

        self._assert_raises_check_access_rule(folder_a_as_internal, "write")
        folder_a_as_portal.check_access("read")
        self._assert_raises_check_access_rule(
            folder_a_a_as_portal, "read", "No access given to A-A"
        )
        self._assert_raises_check_access_rule(folder_a_as_portal, "write")

        portal_access.role = "edit"
        folder_a_as_portal.check_access("write")

        self.folder_a.access_internal = "none"

        self._assert_raises_check_access_rule(folder_a_as_internal)
        folder_a_as_portal.check_access("write")

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_access_from_past_access(self):
        self.folder_a.access_via_link = "view"
        self.folder_a.access_internal = "none"
        self.folder_a_a.access_via_link = "view"
        self.folder_a_a.access_internal = "none"

        self._assert_no_members(self.folder_a)
        self.assertTrue(self.portal_user._is_portal())

        folder_a_as_portal = self.folder_a.with_user(self.portal_user)
        folder_a_a_as_portal = self.folder_a_a.with_user(self.portal_user)
        folder_a_as_internal = self.folder_a.with_user(self.internal_user)
        self.assertEqual(self.folder_a.access_ids.partner_id, self.doc_user.partner_id)
        self._assert_raises_check_access_rule(folder_a_as_portal)
        self.env["document.access"].create(
            {
                "document_id": self.folder_a.id,
                "partner_id": self.portal_user.partner_id.id,
                "last_access_date": fields.Datetime.now(),
            }
        )
        self._assert_raises_check_access_rule(folder_a_as_internal)
        folder_a_as_portal.check_access("read")
        folder_a_a_as_portal.check_access("read")
        self.assertEqual(folder_a_as_portal.user_permission, "view")
        self._assert_raises_check_access_rule(folder_a_as_portal, "write")
        self.folder_a.access_via_link = "edit"
        folder_a_as_portal.check_access("write")
        self._assert_raises_check_access_rule(folder_a_a_as_portal, "write")

        self.folder_a.access_via_link = "none"
        self._assert_raises_check_access_rule(folder_a_as_portal)
        self._assert_raises_check_access_rule(folder_a_a_as_portal)

    def test_access_rights_inherited_on_create(self):
        (self.folder_a + self.folder_b).write(
            {"access_via_link": "none", "access_internal": "none"}
        )
        self._assert_no_members(self.folder_a + self.folder_b)
        folder_a1 = self.env["document.document"].create(
            {"name": "Folder A1", "folder_id": self.folder_a.id, "type": "folder"}
        )
        self.assertEqual(
            folder_a1.access_ids.partner_id, self.folder_a.owner_id.partner_id
        )
        self.assertEqual(folder_a1.access_internal, "none")
        self.assertEqual(folder_a1.access_via_link, "none")
        self.folder_a.access_internal = "view"
        self.assertEqual(len(self.folder_a.access_ids), 1)
        self.folder_a.action_update_access_rights(
            partners={self.portal_user.partner_id.id: ("view", False)}
        )
        self.assertEqual(len(self.folder_a.access_ids), 2)
        self.folder_b.access_via_link = "edit"
        self.folder_b.action_update_access_rights(
            partners={self.portal_user.partner_id.id: (False, False)}
        )
        folder_a2, folder_b1 = self.env["document.document"].create(
            [
                {"name": "Folder A2", "folder_id": self.folder_a.id, "type": "folder"},
                {"name": "Folder B1", "folder_id": self.folder_b.id, "type": "folder"},
            ]
        )
        self.assertEqual(len(folder_a2.access_ids), 2)
        self.assertEqual(
            folder_a2.access_ids.partner_id,
            (self.portal_user + self.doc_user).partner_id,
        )
        self.assertEqual(folder_a2.access_internal, "view")
        self.assertEqual(folder_a2.access_via_link, "none")

        self.assertEqual(folder_b1.access_ids.partner_id, self.doc_user.partner_id)
        self.assertEqual(folder_b1.access_internal, "none")
        self.assertEqual(folder_b1.access_via_link, "edit")

        folder_a3, folder_a4 = self.env["document.document"].create(
            [
                {
                    "name": "Folder A3",
                    "folder_id": self.folder_a.id,
                    "type": "folder",
                    "access_ids": False,
                },
                {
                    "name": "Folder A4",
                    "folder_id": self.folder_a.id,
                    "type": "folder",
                    "access_ids": [
                        Command.create(
                            {
                                "partner_id": self.internal_user.partner_id.id,
                                "role": "view",
                            }
                        )
                    ],
                },
            ]
        )
        self.assertFalse(folder_a3.access_ids)
        self.assertEqual(len(folder_a4.access_ids), 3)
        self.assertEqual(
            folder_a4.access_ids.mapped(lambda a: (a.partner_id, a.role)),
            [
                (self.internal_user.partner_id, "view"),
                (self.portal_user.partner_id, "view"),
                (self.doc_user.partner_id, "edit"),
            ],
        )
        self.folder_a.access_internal = "edit"
        self.folder_a.access_via_link = "view"

        self.env["document.access"].create(
            {
                "document_id": self.folder_a.id,
                "partner_id": self.internal_user.partner_id.id,
                "last_access_date": fields.Datetime.now(),
            }
        )
        self.assertEqual(len(self.folder_a.access_ids), 3)
        folder_a5 = (
            self.env["document.document"]
            .with_context(
                default_access_internal="view", default_folder_id=self.folder_a.id
            )
            .create({"name": "Folder A5", "type": "folder"})
        )
        self.assertEqual(len(folder_a5.access_ids), 2)
        self.assertEqual(
            folder_a5.access_ids.partner_id,
            (self.portal_user + self.doc_user).partner_id,
        )
        self.assertEqual(folder_a5.access_internal, "edit")
        self.assertEqual(folder_a5.access_via_link, "view")

        folder_a6 = (
            self.env["document.document"]
            .with_context(
                default_access_internal="view", default_folder_id=self.folder_a.id
            )
            .create(
                {
                    "name": "Folder A6",
                    "type": "folder",
                    "access_ids": False,
                    "access_internal": "none",
                }
            )
        )
        self.assertFalse(folder_a6.access_ids)
        self.assertEqual(folder_a6.access_internal, "none")
        self.assertEqual(folder_a6.access_via_link, "view")

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_access_owner(self):
        self.folder_a.write({"access_via_link": "none", "access_internal": "none"})
        self._assert_no_members(self.folder_a)
        self._assert_raises_check_access_rule(
            self.folder_a.with_user(self.internal_user)
        )
        self.assertEqual(self.folder_a.owner_id, self.doc_user)
        self.folder_a.with_user(self.doc_user).check_access("read")
        self.folder_a.with_user(self.doc_user).check_access("write")

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_documents_access_cu(self):
        secret = self.env["document.document"].create(
            {
                "access_internal": "none",
                "access_via_link": "none",
                "name": "secret",
            }
        )
        public = self.env["document.document"].create(
            {
                "access_internal": "edit",
                "access_via_link": "none",
                "name": "secret",
            }
        )
        secret_id = secret.id
        self.env.invalidate_all()

        with self.assertRaises(AccessError):
            _ = secret.with_user(self.doc_user).name

        with self.assertRaises(AccessError):
            self.env["document.access"].with_user(self.doc_user).create(
                {
                    "role": "edit",
                    "document_id": secret_id,
                    "partner_id": self.doc_user.partner_id.id,
                }
            )

        with self.assertRaises(AccessError):
            self.env["document.access"].with_user(self.doc_user).with_context(
                default_document_id=secret_id
            ).create(
                {
                    "role": "edit",
                    "partner_id": self.doc_user.partner_id.id,
                }
            )

        access = (
            self.env["document.access"]
            .with_user(self.doc_user)
            .create(
                {
                    "role": "edit",
                    "document_id": public.id,
                    "partner_id": self.doc_user.partner_id.id,
                }
            )
        )
        with self.assertRaises(AccessError):
            access.document_id = secret_id

        with self.assertRaises(AccessError):
            access.copy(default={"document_id": secret_id})

        access_admin = self.env["document.access"].create(
            {
                "role": "edit",
                "document_id": secret_id,
                "partner_id": self.env.user.partner_id.id,
            }
        )
        with self.assertRaises(AccessError):
            access_admin.with_user(self.doc_user).unlink()

        access = self.env["document.access"].create(
            {
                "role": "view",
                "document_id": secret.id,
                "partner_id": self.doc_user.partner_id.id,
            }
        )
        with self.assertRaises(AccessError):
            access.with_user(self.doc_user).role = "edit"

        with self.assertRaises(AccessError):
            access.with_user(self.doc_user).expiration_date = datetime.datetime.now()

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_access_users_drive_is_private(self):
        self.folder_a.write(
            {
                "access_internal": "none",
                "access_via_link": "none",
                "folder_id": False,
                "owner_id": self.internal_user,
            }
        )
        self.folder_a.access_ids = False
        self._assert_no_members(self.folder_a)

        not_authorized = self.doc_user + self.document_manager + self.portal_user
        for not_authorized_user in not_authorized:
            with self.subTest(user=not_authorized_user.name):
                folder_a_with_user = self.folder_a.with_user(not_authorized_user)
                self.assertEqual(
                    self.folder_a.with_user(self.doc_user).user_permission, "none"
                )
                self.assertFalse(
                    folder_a_with_user.search([("id", "=", self.folder_a.id)])
                )
                self._assert_raises_check_access_rule(folder_a_with_user)

        def test_authorized_users(authorized_users):
            for authorized_user in authorized_users:
                folder_a = self.folder_a.with_user(authorized_user)
                with self.subTest(user=authorized_user.name, method="compute"):
                    self.assertEqual(folder_a.user_permission, "edit")
                with self.subTest(user=authorized_user.name, method="search"):
                    self.assertEqual(
                        folder_a.search(
                            [("id", "=", folder_a.id), ("user_permission", "=", "edit")]
                        ),
                        folder_a,
                    )
                    self.assertEqual(
                        folder_a.search([("id", "=", self.folder_a.id)]), self.folder_a
                    )

        self.document_manager.group_ids |= self.env.ref(
            "document.group_documents_system"
        )

        test_authorized_users(self.internal_user + self.document_manager)

        self.folder_a.action_update_access_rights(
            partners={self.portal_user.partner_id: ("edit", False)}
        )
        test_authorized_users(self.portal_user)

        self.folder_a.action_update_access_rights(access_internal="edit")
        test_authorized_users(self.doc_user + self.document_manager)

        self.folder_a.action_update_access_rights(access_internal="view")
        test_authorized_users(self.document_manager)

    @mute_logger("odoo.addons.base.models.ir_rule")
    def _settled_caches(self):
        """Start every pinned block below from ONE known cache state.

        `invalidate_all()` drops the field cache. It does not reset the
        environment's cached `user`/`companies`, nor the registry LRUs behind
        `has_group`, `env.ref` and `get_param` -- but a rolled-back savepoint
        resets all of them. So a block that happened to follow an
        `assertRaises` started colder than one that did not, and the *same*
        call measured 9 queries in one place and 15 in another: the pins were
        reading the history in front of each block rather than the cost of the
        operation.

        The warm-up runs the operation itself, on a throwaway folder, so the
        caches involved are whatever `action_update_access_rights` actually
        touches -- a named list would have to be kept in step with it. The
        field cache is dropped afterwards, so each pin still measures a cold
        read against warm registry caches, which is the state a real request
        reaches this code in.
        """
        scratch = self.env["document.document"].create(
            {"type": "folder", "name": "cache warm-up"}
        )
        scratch.action_update_access_rights(access_internal="view")
        self.env.flush_all()
        self.env.invalidate_all()

    def test_action_update_access_rights_partners(self):
        self._assert_no_members(self.folder_a)
        portal_user_2 = self.portal_user.copy()

        folder_a_as_portal = self.folder_a.with_user(self.portal_user)
        folder_a_as_portal_2 = self.folder_a.with_user(portal_user_2)
        self._assert_raises_check_access_rule(folder_a_as_portal)
        self._assert_raises_check_access_rule(folder_a_as_portal_2)

        IN_ONE_DAY = fields.Datetime.now() + datetime.timedelta(days=1)
        partners = {
            self.portal_user.partner_id.id: ("view", False),
            portal_user_2.partner_id.id: ("view", IN_ONE_DAY),
        }
        self._settled_caches()
        # `user_permission` is a projection of `_search_user_permission` rather
        # than a second Python implementation of it, so the compute flushes what
        # the domain reads (required -- without it it reads stale rows and
        # disagrees with the record rules) and evaluates the domain in SQL. The
        # read path improved with it (kanban page 5 -> 4 queries, 200-document
        # compute 2 -> 1).
        #
        # Every pin in this method is measured from `_settled_caches()`, not
        # from a bare `invalidate_all()`: see its docstring for why the two are
        # not the same measurement.
        with self.assertQueryCount(10):
            self.folder_a.action_update_access_rights(partners=partners)
        folder_a_as_portal.check_access("read")
        folder_a_as_portal_2.check_access("read")
        folder_a_as_internal = self.folder_a.with_user(self.internal_user)

        portal_2_a_a_access = self.folder_a_a.access_ids.filtered(
            lambda a: a.partner_id == portal_user_2.partner_id
        )
        self.assertEqual(len(portal_2_a_a_access), 1)
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_ONE_DAY)
        IN_12_H = IN_ONE_DAY - datetime.timedelta(hours=12)
        self._settled_caches()
        with self.assertQueryCount(10):
            self.folder_a.action_update_access_rights(
                partners={portal_user_2.partner_id: ("view", IN_12_H)}
            )
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_12_H)

        # Update role+expiration via parent
        self._settled_caches()
        with self.assertQueryCount(10):
            self.folder_a.action_update_access_rights(
                partners={portal_user_2.partner_id: ("edit", IN_ONE_DAY)}
            )
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_ONE_DAY)
        self.assertEqual(portal_2_a_a_access.role, "edit")

        # Update role alone via parent
        self._settled_caches()
        with self.assertQueryCount(10):
            self.folder_a.action_update_access_rights(
                partners={portal_user_2.partner_id: ("view", None)}
            )
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_ONE_DAY)
        self.assertEqual(portal_2_a_a_access.role, "view")

        # Update expiration alone via parent: the role is left as it is, and
        # a partner who is not a member gains nothing.
        self._settled_caches()
        self.folder_a.action_update_access_rights(
            partners={
                portal_user_2.partner_id: (None, IN_12_H),
                self.internal_user.partner_id: (None, IN_12_H),
            }
        )
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_12_H)
        self.assertEqual(portal_2_a_a_access.role, "view")
        self.assertFalse(
            (self.folder_a | self.folder_a_a).access_ids.filtered(
                lambda a: a.partner_id == self.internal_user.partner_id and a.role
            )
        )

        partners = {self.portal_user.partner_id.id: (False, None)}

        self._settled_caches()
        with self.assertQueryCount(12):
            self.folder_a.action_update_access_rights(partners=partners)
            self.assertFalse(
                self.folder_a.access_ids.filtered(
                    lambda a: a.partner_id == self.portal_user.partner_id
                )
            )
        self._assert_raises_check_access_rule(folder_a_as_portal, "read")

        folder_a_a_p = self.env["document.document"].create(
            {
                "type": "folder",
                "name": "A cool name",
                "folder_id": self.folder_a_a.id,
            }
        )

        partners = {self.portal_user.partner_id.id: ("view", False)}
        self._settled_caches()
        with self.assertQueryCount(9):
            folder_a_a_p.action_update_access_rights(partners=partners)

        partners = dict.fromkeys(
            (self.portal_user | self.internal_user).partner_id.ids, ("edit", False)
        )
        self._settled_caches()
        with self.assertQueryCount(10):
            self.folder_a.action_update_access_rights(partners=partners)
        folder_a_as_portal.check_access("write")
        folder_a_a_as_portal = self.folder_a_a.with_user(self.portal_user)
        folder_a_a_as_portal.check_access("write")
        folder_a_as_internal.check_access("write")

        self._assert_raises_check_access_rule(folder_a_as_portal_2, "write")

        portal_2_partner_id = portal_user_2.partner_id.id
        self._settled_caches()
        with self.assertQueryCount(9):
            self.folder_a.action_update_access_rights(
                partners={portal_2_partner_id: (False, False)}
            )
        self._assert_raises_check_access_rule(folder_a_as_portal_2)

        # Add portal 2 access to 1st level child and remove from 2nd
        self._settled_caches()
        with self.assertQueryCount(9):
            self.folder_a_a.action_update_access_rights(
                partners={portal_2_partner_id: ("view", False)}
            )
        folder_a_a_p.action_update_access_rights(
            partners={portal_user_2.partner_id.id: (False, None)}
        )
        self.assertFalse(
            folder_a_a_p.access_ids.filtered(
                lambda a: a.partner_id == portal_user_2.partner_id
            )
        )

        folder_a_a_p.action_archive()
        self.folder_a_a.action_update_access_rights(
            partners={portal_user_2.partner_id.id: ("edit", None)}
        )
        self.assertEqual(
            folder_a_a_p.access_ids.filtered(
                lambda a: a.partner_id == portal_user_2.partner_id
            ).role,
            "edit",
        )

    def test_action_update_access_rights_internal_propagation(self):
        self.assertEqual(
            set((self.folder_b + self.document_gif).mapped("access_internal")), {"view"}
        )
        self.folder_b.action_update_access_rights(access_internal="none")
        self.assertEqual(
            set((self.folder_b + self.document_gif).mapped("access_internal")), {"none"}
        )

        self.document_gif.action_archive()
        self.folder_b.action_update_access_rights(access_internal="edit")
        self.assertEqual(
            set((self.folder_b + self.document_gif).mapped("access_internal")), {"edit"}
        )

        self.document_gif.action_update_access_rights(access_internal="view")
        self.assertEqual(
            (self.folder_b + self.document_gif).mapped("access_internal"),
            ["edit", "view"],
        )

    def test_action_update_access_rights_no_propagation(self):
        doc_partner = self.doc_user.partner_id
        self.folder_b.action_update_access_rights(
            access_internal="view",
            access_via_link="view",
            is_access_via_link_hidden=True,
            partners={self.doc_user.partner_id: ("view", False)},
        )
        self.assertEqual(
            self.folder_b.access_ids.filtered(
                lambda a: a.partner_id == doc_partner
            ).mapped(lambda a: (a.role, a.expiration_date)),
            [("view", False)],
        )
        self.assertEqual(
            self.document_gif.access_ids.filtered(
                lambda a: a.partner_id == doc_partner
            ).mapped(lambda a: (a.role, a.expiration_date)),
            [("view", False)],
        )
        self.assertEqual(
            self.folder_b.mapped(
                lambda d: (
                    d.access_internal,
                    d.access_via_link,
                    d.is_access_via_link_hidden,
                )
            ),
            [("view", "view", True)],
        )
        self.assertEqual(
            self.document_gif.mapped(lambda d: (d.access_internal, d.access_via_link)),
            [("view", "view")],
        )
        self.assertFalse(
            self.document_gif.is_access_via_link_hidden,
            "`is_access_via_link_hidden` should not propagate",
        )
        IN_ONE_DAY = fields.Datetime.now() + datetime.timedelta(days=1)
        self.document_txt.is_access_via_link_hidden = True

        self.folder_b.action_update_access_rights(
            access_internal="edit",
            access_via_link="edit",
            is_access_via_link_hidden=False,
            partners={doc_partner: ("edit", IN_ONE_DAY)},
            no_propagation=True,
        )

        self.assertEqual(
            self.folder_b.mapped(
                lambda d: (
                    d.access_internal,
                    d.access_via_link,
                    d.is_access_via_link_hidden,
                )
            ),
            [("edit", "edit", False)],
        )
        self.assertEqual(
            self.folder_b.access_ids.filtered(
                lambda a: a.partner_id == doc_partner
            ).mapped(lambda a: (a.role, a.expiration_date)),
            [("edit", IN_ONE_DAY)],
        )

        self.assertEqual(
            self.document_gif.mapped(
                lambda d: (
                    d.access_internal,
                    d.access_via_link,
                    d.is_access_via_link_hidden,
                )
            ),
            [("view", "view", False)],
        )
        self.assertEqual(
            self.document_txt.mapped(
                lambda d: (
                    d.access_internal,
                    d.access_via_link,
                    d.is_access_via_link_hidden,
                )
            ),
            [("view", "view", True)],
        )
        self.assertEqual(
            self.document_gif.access_ids.filtered(
                lambda a: a.partner_id == doc_partner
            ).mapped(lambda a: (a.role, a.expiration_date)),
            [("view", False)],
        )

    def test_action_update_access_rights_link_propagation(self):
        self.assertEqual(
            set((self.folder_b + self.document_gif).mapped("access_via_link")), {"none"}
        )
        self.folder_b.action_update_access_rights(access_via_link="view")
        self.assertEqual(
            set((self.folder_b + self.document_gif).mapped("access_via_link")), {"view"}
        )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_action_update_access_rights_sudo(self):
        self.folder_a.write(
            {
                "access_internal": "none",
                "access_via_link": "none",
                "folder_id": False,
                "owner_id": self.document_manager,
            }
        )
        self.folder_a.access_ids = False
        self._assert_no_members(self.folder_a)
        folder_a_as_internal = self.folder_a.with_user(self.internal_user)
        with self.assertRaises(AccessError):
            folder_a_as_internal.action_update_access_rights(
                partners={self.internal_user.partner_id: ("edit", None)}
            )
        folder_a_as_internal.sudo().action_update_access_rights(
            partners={self.internal_user.partner_id: ("edit", None)}
        )

    @users("documents@example.com")
    def test_moving_documents(self):
        self.folder_b.write(
            {
                "access_internal": "none",
                "access_via_link": "none",
                "is_access_via_link_hidden": True,
            }
        )
        self.folder_a.write(
            {"access_via_link": "view", "is_access_via_link_hidden": False}
        )
        self.folder_a_a.folder_id = self.folder_b.id
        self.assertEqual(self.folder_a_a.folder_id, self.folder_b)

        self.folder_b.folder_id = self.folder_a.id

        self.assertEqual(self.folder_b.folder_id, self.folder_a)
        self.assertEqual(
            self.folder_b.access_internal,
            "view",
            "Internal access should have been updated.",
        )
        self.assertEqual(
            self.folder_b.access_via_link,
            "view",
            "link access should have been updated.",
        )
        self.assertEqual(
            self.folder_b.is_access_via_link_hidden,
            True,
            "Discoverability should not be updated",
        )

        self.document_gif.folder_id = False
        shortcut = self.folder_b.with_user(self.doc_user).action_create_shortcut(
            location_user_folder_id="MY"
        )
        self.document_gif.folder_id = shortcut.id
        self.assertEqual(self.document_gif.folder_id, self.folder_b)

        doc_shortcut = self.document_gif.action_create_shortcut(str(shortcut.id))
        self.assertEqual(doc_shortcut.folder_id, self.folder_b)

        shortcut = shortcut.action_create_shortcut(location_user_folder_id="MY")
        self.assertEqual(shortcut.shortcut_document_id, self.folder_b)

        self.folder_a.action_update_access_rights(
            partners={self.internal_user.partner_id.id: ("edit", False)}
        )
        self.folder_b.action_update_access_rights(
            partners={self.internal_user.partner_id.id: ("view", False)}
        )
        with self.assertRaises(AccessError):
            self.document_gif.with_user(self.internal_user).folder_id = self.folder_a

        with self.assertRaises(AccessError):
            self.document_gif.with_user(self.internal_user).folder_id = self.folder_a.id

        self.document_gif.owner_id = self.internal_user
        self.document_gif.with_user(self.internal_user).folder_id = self.folder_a

    def test_ir_actions_server(self):
        self.internal_user.group_ids |= self.env.ref("document.group_documents_user")
        document = self.document_gif.with_user(self.internal_user)
        document.sudo().access_internal = "edit"

        self.assertEqual(document.user_permission, "edit")
        self.assertEqual(document.folder_id.user_permission, "view")
        self.assertEqual(self.folder_a.user_permission, "edit")
        with self.assertRaises(AccessError):
            document.folder_id = self.folder_a

        action_base_values = {
            "name": "Test Action",
            "model_id": self.env["ir.model"]._get_id("document.document"),
            "update_path": "folder_id",
            "usage": "documents_embedded",
            "resource_ref": f"document.document,{self.folder_a.id}",
        }

        action = (
            self.env["ir.actions.server"]
            .create(
                {
                    **action_base_values,
                    "state": "multi",
                    "child_ids": [
                        Command.create(
                            {
                                **action_base_values,
                                "state": "multi",
                                "child_ids": [
                                    Command.create(
                                        {
                                            **action_base_values,
                                            "state": "object_write",
                                        }
                                    )
                                ],
                            }
                        )
                    ],
                }
            )
            .with_user(self.internal_user)
        )

        with self.assertRaises(UserError):
            action.with_context(
                active_model="document.document", active_id=document.id
            ).run()

        self.env["document.document"].action_folder_embed_action(
            document.folder_id.id, action.id
        )

        action.with_context(
            active_model="document.document", active_id=document.id
        ).run()
        self.assertEqual(document.folder_id, self.folder_a)

        with self.assertRaises(UserError):
            action.with_context(
                active_model="document.document", active_id=document.id
            ).run()

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule")
    def test_create_document_access(self):
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).name = "test"

        with self.assertRaises(AccessError):
            self.env["document.document"].with_user(self.internal_user).create(
                {
                    "name": "folder",
                    "folder_id": self.folder_a.id,
                    "owner_id": self.internal_user.id,
                    "type": "folder",
                }
            )

        self.env["document.document"].with_user(self.internal_user).create(
            {
                "name": "document",
                "folder_id": False,
                "owner_id": self.internal_user.id,
                "type": "binary",
            }
        )

        with self.assertRaises(UserError):
            self.env["document.document"].with_user(self.portal_user).create(
                {
                    "name": "document",
                    "folder_id": False,
                    "owner_id": self.portal_user.id,
                    "type": "binary",
                }
            )

        with self.assertRaises(UserError):
            self.env["document.document"].with_user(self.portal_user).create(
                {
                    "name": "document",
                    "folder_id": False,
                    "owner_id": self.internal_user.id,
                    "type": "binary",
                }
            )

        self.env["document.document"].with_user(self.portal_user).sudo().create(
            {
                "name": "document",
                "folder_id": False,
                "owner_id": self.internal_user.id,
                "type": "binary",
            }
        )

        with self.assertRaises(UserError):
            self.env["document.document"].with_user(self.portal_user).sudo().create(
                {
                    "name": "document",
                    "folder_id": False,
                    "owner_id": self.portal_user.id,
                    "type": "binary",
                }
            )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_restrict_write_on_pinned_folders(self):
        self.assertFalse(self.folder_a.folder_id)
        self.folder_a.owner_id = False
        self.folder_a.action_update_access_rights(
            partners={self.internal_user.partner_id.id: ("edit", False)}
        )
        access = self.env["document.access"].search(
            [
                ("document_id", "=", self.folder_a.id),
                ("partner_id", "=", self.internal_user.partner_id.id),
            ]
        )
        self.assertEqual(len(access), 1)
        self.assertEqual(access.role, "edit")
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).folder_id = self.folder_b
        self._assert_raises_check_access_rule(
            self.folder_a.with_user(self.internal_user), "write"
        )
        self.assertEqual(
            self.folder_a.with_user(self.internal_user).user_permission, "edit"
        )
        self.env["document.document"].with_user(self.internal_user).create(
            {"type": "folder", "name": "a folder", "folder_id": self.folder_a.id}
        )
        shortcut = self.document_txt.with_user(
            self.internal_user
        ).action_create_shortcut(location_user_folder_id=str(self.folder_a.id))
        self.assertEqual(shortcut.folder_id, self.folder_a)
        self.folder_b.owner_id = False
        self.folder_a.with_user(self.document_manager).folder_id = self.folder_b
        self.assertFalse(self.folder_a._is_company_root_folder())
        self.folder_a.with_user(self.document_manager).folder_id = False
        self.folder_a.with_user(self.document_manager).owner_id = self.document_manager

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_pin_folder_create(self):
        folder = self.env["document.document"].create(
            {
                "folder_id": False,
                "name": "folder",
                "owner_id": False,
                "type": "folder",
            }
        )
        self.assertTrue(folder._is_company_root_folder())

        with self.assertRaises(AccessError):
            self.env["document.document"].with_user(self.internal_user).create(
                {
                    "folder_id": False,
                    "name": "folder",
                    "owner_id": False,
                    "type": "folder",
                }
            )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_pin_folder_folder_id(self):
        self.assertFalse(self.folder_a.folder_id)

        self.folder_a.owner_id = self.document_manager
        self.folder_a.access_ids = False
        self.folder_a.action_update_access_rights(
            access_internal="none",
            partners={self.internal_user.partner_id.id: ("edit", False)},
        )
        children_access_before = [
            access_ids.filtered(lambda a: a.role)
            for access_ids in self.folder_a.children_ids.mapped(lambda f: f.access_ids)
        ]
        for child_access_before in children_access_before:
            self.assertFalse(
                self.document_manager.partner_id & child_access_before.partner_id
            )

        self.folder_a.with_user(self.document_manager).user_folder_id = "COMPANY"
        self.assertEqual(
            (self.document_manager | self.internal_user).partner_id,
            self.folder_a.access_ids.filtered(lambda a: a.role).partner_id,
        )
        self.assertEqual(
            [
                access_ids.filtered(lambda a: a.role)
                for access_ids in self.folder_a.children_ids.mapped(
                    lambda f: f.access_ids
                )
            ],
            children_access_before,
        )

        self._assert_raises_check_access_rule(
            self.folder_a.with_user(self.internal_user), "write"
        )

        self.folder_b.children_ids.action_update_access_rights(
            partners={self.doc_user.partner_id: (False, False)}
        )
        self.folder_b.folder_id = False
        self.assertEqual(self.folder_b.owner_id, self.doc_user)
        self.folder_b.action_update_access_rights(
            access_internal="edit",
            partners={self.internal_user.partner_id.id: ("edit", False)},
        )
        children_access_before = [
            access_ids.filtered(lambda a: a.role)
            for access_ids in self.folder_b.children_ids.mapped(lambda f: f.access_ids)
        ]
        for child_access_before in children_access_before:
            self.assertFalse(self.doc_user.partner_id & child_access_before.partner_id)

        self.folder_b.with_user(self.document_manager).user_folder_id = "COMPANY"
        self.assertEqual(
            (self.doc_user | self.internal_user).partner_id,
            self.folder_b.access_ids.filtered(lambda a: a.role).partner_id,
        )

        self.assertEqual(
            [
                access_ids.filtered(lambda a: a.role)
                for access_ids in self.folder_b.children_ids.mapped(
                    lambda f: f.access_ids
                )
            ],
            children_access_before,
        )

        self.assertFalse((self.folder_a | self.folder_b).owner_id)

        self.folder_a.with_user(self.document_manager).owner_id = self.internal_user

        self.folder_a.with_user(self.internal_user).check_access("write")
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).user_folder_id = "COMPANY"

        self.folder_a.with_user(self.internal_user).sudo().user_folder_id = "COMPANY"
        self.folder_a.with_user(self.internal_user).sudo().owner_id = self.internal_user

        with self.assertRaises(AccessError):
            self.company_root_folder.with_user(self.internal_user).copy(
                default={"user_folder_id": "COMPANY"}
            )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_unlink_with_children(self):
        self.folder_a.action_update_access_rights(access_internal="edit")
        self.folder_a_a.action_update_access_rights(access_internal="none")
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).unlink()
        self.folder_a_a.action_update_access_rights(access_internal="edit")
        self.folder_a.with_user(self.internal_user).unlink()
        self.assertFalse(self.folder_a_a.exists())

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_archiving_with_children(self):
        self.folder_a.action_update_access_rights(access_internal="edit")
        self.folder_a_a.action_update_access_rights(access_internal="none")
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).action_archive()
        self.folder_a_a.action_update_access_rights(access_internal="edit")
        self.folder_a.with_user(self.internal_user).action_archive()
        self.assertFalse(self.folder_a_a.active)

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_access_expiration(self):
        self._assert_no_members(self.folder_a)
        self.folder_a.action_update_access_rights(
            partners={self.portal_user.partner_id.id: ("view", False)}
        )
        folder_a_as_portal = self.folder_a.with_user(self.portal_user)
        folder_a_as_portal.check_access("read")
        first_child_as_portal = folder_a_as_portal.children_ids
        self.folder_a.action_update_access_rights(
            partners={
                self.portal_user.partner_id.id: (
                    "view",
                    fields.Datetime.now() - datetime.timedelta(days=1),
                )
            }
        )
        self.assertEqual(len(first_child_as_portal), 1)
        self._assert_raises_check_access_rule(folder_a_as_portal, "read")
        self._assert_raises_check_access_rule(first_child_as_portal, "read")

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_access_via_link_from_parent_folder(self):
        self._assert_no_members(self.folder_b)
        self.folder_b.action_update_access_rights(
            access_internal="none", access_via_link="none"
        )
        self.assertEqual(self.folder_b.access_internal, "none")
        self.assertEqual(self.document_gif.access_internal, "none")
        self.assertEqual(self.document_txt.access_internal, "none")
        self.assertEqual(self.document_gif.access_via_link, "none")
        # Propagation reaches the children for BOTH fields of that one call.
        # This used to assert "view" -- the value `setUpClass` wrote onto this
        # document directly -- because the walk was seeded only from rows whose
        # value differed and `folder_b` already held `access_via_link="none"`.
        # So one field of the call propagated and the other silently did not,
        # decided by what the folder happened to hold rather than by what was
        # asked for. `TestAccessPropagation` pins the general case.
        self.assertEqual(self.document_txt.access_via_link, "none")

        # What the rest of this test is about is link access INHERITED from the
        # parent folder, and it needs this document to carry its own. Put it
        # back the way `setUpClass` had it -- deliberately and after the
        # propagation, rather than by surviving it.
        self.document_txt.access_via_link = "view"
        with mute_logger("odoo.addons.document.models.document_document"):
            document_txt_private = self.document_txt.copy()
        self.assertIn(document_txt_private.access_ids.role, {False, "edit"})
        document_txt_private.is_access_via_link_hidden = True
        self.assertEqual(document_txt_private.access_via_link, "view")

        gif_as_internal = self.document_gif.with_user(self.internal_user)
        txt_as_internal = self.document_txt.with_user(self.internal_user)
        txt_private_as_internal = document_txt_private.with_user(self.internal_user)

        self._assert_raises_check_access_rule(gif_as_internal | txt_as_internal, "read")

        access_values = {
            "document_id": self.folder_b.id,
            "partner_id": self.internal_user.partner_id.id,
        }
        folder_accesses_values = [
            ("internal user access", {"access_internal": "view"}),
            (
                "link accessed",
                {
                    "access_via_link": "view",
                    "access_ids": [
                        Command.create(
                            access_values | {"last_access_date": fields.Datetime.now()}
                        )
                    ],
                },
            ),
            (
                "member",
                {"access_ids": [Command.create(access_values | {"role": "view"})]},
            ),
        ]
        for case_name, folder_access_vals in folder_accesses_values:
            with self.subTest(case_name=case_name):
                self.folder_b.write(folder_access_vals)
                self._assert_raises_check_access_rule(gif_as_internal, "read")
                self._assert_raises_check_access_rule(txt_private_as_internal, "read")
                self.assertEqual(
                    (gif_as_internal | txt_private_as_internal).mapped(
                        "user_permission"
                    ),
                    ["none", "none"],
                )
                self.assertEqual(
                    txt_as_internal.search([("folder_id", "=", self.folder_b.id)]),
                    self.document_txt,
                )
                txt_as_internal.check_access("read")
                if case_name == "internal user access":
                    self._assert_raises_check_access_rule(
                        self.document_txt.with_user(self.portal_user), "read"
                    )

            self.folder_b.write({"access_internal": "none", "access_via_link": "none"})
            self.folder_b.access_ids.unlink()

    def test_access_documents_and_attachment(self):
        self.document_gif.action_update_access_rights(
            access_internal="none", access_via_link="none"
        )
        gif_as_internal = self.document_gif.with_user(self.internal_user)

        self.assertFalse(self.document_gif.res_id)
        self.assertFalse(self.document_gif.res_model)

        self.assertEqual(self.document_gif.attachment_id.res_id, self.document_gif.id)
        self.assertEqual(self.document_gif.attachment_id.res_model, "document.document")

        self._assert_raises_check_access_rule(gif_as_internal, "read")

        self.assertFalse(self.document_gif.res_model)
        with self.assertRaises(AccessError):
            self.assertEqual(
                self.document_gif.attachment_id.with_user(self.internal_user).name,
                "file.gif",
            )

        self.document_gif.access_internal = "view"
        self.assertEqual(gif_as_internal.with_user(self.internal_user).name, "file.gif")
        self.assertFalse(gif_as_internal.res_model)
        self.env.invalidate_all()
        self.assertEqual(
            self.document_gif.attachment_id.with_user(self.internal_user).name,
            "file.gif",
        )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_access_rights_shortcuts_and_discoverability(self):
        self._assert_no_members(self.folder_b)
        self.folder_b.folder_id = self.folder_a.id
        self.assertEqual(
            (self.folder_b + self.document_txt).access_ids.mapped("role"),
            [False, "edit"],
        )
        self.folder_a.owner_id = False

        self.assertEqual(self.folder_a.access_internal, "view")
        self.assertEqual(self.document_txt.folder_id, self.folder_b)

        self.folder_a.action_update_access_rights(
            partners={self.portal_user.partner_id: ("view", False)}
        )
        (self.folder_b + self.document_txt).action_update_access_rights(
            access_internal="none",
            access_via_link="none",
            partners={self.portal_user.partner_id: (False, False)},
        )

        self.assertEqual(
            self.document_txt.with_user(self.portal_user).user_permission, "none"
        )

        self._assert_raises_check_access_rule(
            self.document_txt.with_user(self.portal_user), "read"
        )

        shortcut = self.document_txt.action_create_shortcut(
            location_user_folder_id=str(self.folder_a.id)
        )

        self.assertEqual(
            shortcut.access_ids.mapped(lambda a: (a.role, a.partner_id)),
            [("edit", self.doc_user.partner_id)],
        )
        self._assert_raises_check_access_rule(
            shortcut.with_user(self.portal_user),
            "read",
            "Shortcut shouldn't be visible as source is inaccessible",
        )
        self.assertEqual(shortcut.with_user(self.portal_user).user_permission, "none")

        docs = self.document_txt + shortcut

        self.assertSetEqual(
            set(docs.with_user(self.internal_user).mapped("user_permission")), {"none"}
        )
        self._assert_raises_check_access_rule(
            docs.with_user(self.internal_user), "read"
        )

        self.assertSetEqual(
            set(docs.with_user(self.document_manager).mapped("user_permission")),
            {"none"},
        )
        self._assert_raises_check_access_rule(
            docs.with_user(self.document_manager), "read"
        )

        self.document_txt.action_update_access_rights(access_internal="view")
        self.assertSetEqual(
            set(docs.with_user(self.internal_user).mapped("user_permission")), {"view"}
        )
        docs.with_user(self.internal_user).check_access("read")

        self.assertSetEqual(
            set(docs.with_user(self.document_manager).mapped("user_permission")),
            {"edit"},
        )
        docs.with_user(self.document_manager).check_access("write")

        self.assertSetEqual(
            set(docs.with_user(self.portal_user).mapped("user_permission")), {"none"}
        )
        self._assert_raises_check_access_rule(docs.with_user(self.portal_user), "read")

        self.document_txt.action_update_access_rights(
            access_via_link="view", is_access_via_link_hidden=True
        )
        self.assertEqual(shortcut.access_via_link, "view")
        self.assertEqual(shortcut.is_access_via_link_hidden, True)
        self._assert_raises_check_access_rule(
            shortcut.with_user(self.portal_user),
            "read",
            "Shortcut shouldn't be visible as source is still inaccessible",
        )
        self.assertEqual(shortcut.with_user(self.portal_user).user_permission, "none")

        self.document_txt.action_update_access_rights(is_access_via_link_hidden=False)
        self.assertEqual(self.document_txt.is_access_via_link_hidden, False)
        self.assertEqual(shortcut.is_access_via_link_hidden, False)
        self.assertEqual(shortcut.with_user(self.portal_user).user_permission, "view")
        shortcut.with_user(self.portal_user).check_access("read")

        self._assert_raises_check_access_rule(
            self.document_txt.with_user(self.portal_user), "read"
        )

        partner = self.env["res.partner"].create({"name": "Test"})
        shortcut.shortcut_document_id.action_update_access_rights(
            access_internal="edit", partners={partner: ("edit", False)}
        )
        self.assertEqual(shortcut.shortcut_document_id.access_internal, "edit")
        self.assertEqual(shortcut.access_internal, "edit")

        access = self.env["document.access"].search([("partner_id", "=", partner.id)])
        self.assertEqual(len(access), 2)
        self.assertEqual(access.document_id, shortcut | shortcut.shortcut_document_id)

        shortcut.shortcut_document_id.action_update_access_rights(
            access_internal="edit", partners={partner: (False, False)}
        )
        self.assertFalse(access.exists())

        self.folder_a.action_update_access_rights(access_internal="edit")
        self.document_txt.action_update_access_rights(
            access_internal="view", access_via_link="none"
        )

        shortcut = self.document_txt.with_user(
            self.internal_user
        ).action_create_shortcut(location_user_folder_id=str(self.folder_a.id))
        self.assertEqual(shortcut.owner_id, self.internal_user)
        self.document_txt.action_update_access_rights(access_internal="none")
        self.assertEqual(
            self.document_txt.with_user(self.internal_user).user_permission, "none"
        )
        self.assertFalse(
            self.env["document.document"]
            .with_user(self.internal_user)
            .search([("id", "=", shortcut.id)])
        )
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "none")

        self.document_txt.action_update_access_rights(
            partners={self.internal_user.partner_id: ("view", False)}
        )
        shortcut = self.document_txt.with_user(
            self.internal_user
        ).action_create_shortcut(location_user_folder_id=str(self.folder_a.id))
        self.assertEqual(shortcut.owner_id, self.internal_user)
        self.document_txt.action_update_access_rights(
            partners={self.internal_user.partner_id: (False, False)}
        )
        self.assertFalse(
            self.env["document.document"]
            .with_user(self.internal_user)
            .search([("id", "=", shortcut.id)])
        )
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "none")

        self.document_txt.owner_id = self.internal_user
        shortcut = self.document_txt.with_user(
            self.internal_user
        ).action_create_shortcut(location_user_folder_id=str(self.folder_a.id))
        self.assertEqual(shortcut.owner_id, self.internal_user)
        self.document_txt.owner_id = self.document_manager
        self.assertFalse(
            self.env["document.document"]
            .with_user(self.internal_user)
            .search([("id", "=", shortcut.id)])
        )
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "none")

    def test_access_rights_shortcuts_target(self):
        Doc_as_internal = self.env["document.document"].with_user(self.internal_user)
        Doc_as_internal_sudo = Doc_as_internal.sudo()
        shortcut = self.document_txt.action_create_shortcut(
            location_user_folder_id=str(self.folder_a.id)
        )

        self.document_txt.action_update_access_rights(
            access_internal="view", access_via_link="none"
        )
        shortcut.sudo().owner_id = self.internal_user
        self.assertEqual(
            self.document_txt.with_user(self.internal_user).user_permission, "view"
        )
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "edit")
        self.assertTrue(
            Doc_as_internal_sudo.search(
                [("id", "=", shortcut.id), ("user_permission", "=", "edit")]
            )
        )
        doc_class = Doc_as_internal_sudo.pool["document.document"]

        original_search = doc_class._search_user_permission

        with patch.object(
            doc_class,
            "_search_user_permission",
            autospec=True,
            side_effect=original_search,
        ) as patched_search_user_permission:
            self.assertTrue(
                Doc_as_internal_sudo.search(
                    [("id", "=", shortcut.id), ("user_permission", "!=", "none")]
                )
            )
            self.assertEqual(patched_search_user_permission.call_count, 1)

        self.document_txt.action_update_access_rights(access_internal="none")
        self.assertEqual(
            self.document_txt.with_user(self.internal_user).user_permission, "none"
        )
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "none")
        self.assertFalse(Doc_as_internal.search([("id", "=", shortcut.id)]))
        with patch.object(
            doc_class,
            "_search_user_permission",
            autospec=True,
            side_effect=original_search,
        ) as patched_search_user_permission:
            self.assertFalse(
                Doc_as_internal_sudo.search(
                    [("id", "=", shortcut.id), ("user_permission", "=", "edit")]
                )
            )
            self.assertEqual(patched_search_user_permission.call_count, 1)
        self.assertFalse(
            Doc_as_internal_sudo.search(
                [("id", "=", shortcut.id), ("user_permission", "=", "view")]
            )
        )

        self.document_txt.sudo().owner_id = self.internal_user
        self.assertEqual(
            self.document_txt.with_user(self.internal_user).user_permission, "edit"
        )
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "edit")
        self.assertTrue(
            Doc_as_internal_sudo.search(
                [("id", "=", shortcut.id), ("user_permission", "=", "edit")]
            )
        )
        self.assertTrue(
            Doc_as_internal_sudo.search(
                [("id", "=", shortcut.id), ("user_permission", "!=", "none")]
            )
        )
        self.assertFalse(
            Doc_as_internal_sudo.search(
                [("id", "=", shortcut.id), ("user_permission", "=", "view")]
            )
        )

    def test_access_rights_shortcuts_target_accessible_via_link(self):
        Doc_as_internal_sudo = (
            self.env["document.document"].with_user(self.internal_user).sudo()
        )
        self.folder_a.access_internal = "edit"

        self.document_txt.folder_id.action_update_access_rights(access_internal="view")
        self.document_txt.action_update_access_rights(
            access_internal="none",
            access_via_link="view",
            is_access_via_link_hidden=False,
        )
        self.env["document.access"].create(
            [
                {
                    "document_id": self.document_txt.id,
                    "partner_id": self.internal_user.partner_id.id,
                    "last_access_date": fields.Datetime.now(),
                }
            ]
        )
        shortcut = self.document_txt.with_user(
            self.internal_user
        ).action_create_shortcut(location_user_folder_id=str(self.folder_a.id))
        self.assertEqual(
            self.document_txt.with_user(self.internal_user).user_permission, "view"
        )
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "edit")
        self.assertTrue(
            Doc_as_internal_sudo.search(
                [("id", "=", shortcut.id), ("user_permission", "=", "edit")]
            )
        )
        self.assertTrue(
            Doc_as_internal_sudo.search(
                [("id", "=", shortcut.id), ("user_permission", "!=", "none")]
            )
        )

        self.document_txt.action_update_access_rights(access_via_link="none")
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "none")
        self.assertEqual(shortcut.with_user(self.internal_user).user_permission, "none")

    @mute_logger("odoo.addons.base.models.ir_rule")
    @users("documents@example.com")
    def test_access_rights_shortcuts_propagation(self):
        target = self.env["document.document"].create(
            {
                "name": "Target",
                "access_internal": "edit",
            }
        )

        root = self.env["document.document"].create(
            {
                "name": "Root",
                "type": "folder",
                "access_internal": "edit",
                "children_ids": [
                    Command.create(
                        {
                            "name": "A",
                            "type": "folder",
                            "access_internal": "edit",
                            "is_access_via_link_hidden": True,
                            "children_ids": [
                                Command.create(
                                    {
                                        "name": "File 1",
                                        "access_internal": "edit",
                                    }
                                ),
                                Command.create(
                                    {
                                        "name": "File 2",
                                        "access_internal": "view",
                                    }
                                ),
                                Command.create(
                                    {
                                        "name": "File 3",
                                        "access_internal": "none",
                                        "access_via_link": "edit",
                                        "is_access_via_link_hidden": False,
                                    }
                                ),
                                Command.create(
                                    {
                                        "name": "Sub-folder",
                                        "type": "folder",
                                        "access_internal": "edit",
                                        "children_ids": [
                                            Command.create(
                                                {
                                                    "name": "Sub-file",
                                                    "access_internal": "edit",
                                                }
                                            )
                                        ],
                                    }
                                ),
                                Command.create(
                                    {
                                        "name": "Shortcut",
                                        "access_internal": "edit",
                                        "shortcut_document_id": target.id,
                                    }
                                ),
                            ],
                        }
                    )
                ],
                "owner_id": self.document_manager.id,
            }
        )

        file_1 = self.env["document.document"].search(
            [("id", "child_of", root.id), ("name", "=", "File 1")]
        )
        file_2 = self.env["document.document"].search(
            [("id", "child_of", root.id), ("name", "=", "File 2")]
        )
        file_3 = self.env["document.document"].search(
            [("id", "child_of", root.id), ("name", "=", "File 3")]
        )
        shortcut = self.env["document.document"].search(
            [("id", "child_of", root.id), ("name", "=", "Shortcut")]
        )
        sub_folder = self.env["document.document"].search(
            [("id", "child_of", root.id), ("name", "=", "Sub-folder")]
        )
        sub_file = self.env["document.document"].search(
            [("id", "child_of", root.id), ("name", "=", "Sub-file")]
        )
        shortcut_1 = file_1.action_create_shortcut(location_user_folder_id="MY")
        shortcut_2 = file_2.action_create_shortcut(location_user_folder_id="MY")
        shortcut_3 = file_3.action_create_shortcut(location_user_folder_id="MY")
        self.assertEqual(shortcut_1.access_internal, "edit")
        self.assertEqual(shortcut_2.access_internal, "view")
        self.assertEqual(shortcut_3.access_internal, "none")

        self.assertEqual(file_2.with_user(self.internal_user).user_permission, "view")
        self.assertEqual(
            shortcut_2.with_user(self.internal_user).user_permission, "view"
        )

        self.assertEqual(file_3.with_user(self.internal_user).user_permission, "edit")
        self.assertEqual(
            shortcut_3.with_user(self.internal_user).user_permission, "none"
        )

        root.with_user(self.internal_user).action_update_access_rights(
            access_via_link="view"
        )

        self.assertEqual(root.access_via_link, "view")
        self.assertEqual(file_1.access_via_link, "view")
        self.assertEqual(file_2.access_via_link, "none")
        self.assertEqual(file_3.access_via_link, "view")
        self.assertEqual(shortcut_1.access_via_link, "view")
        self.assertEqual(shortcut_2.access_via_link, "none")
        self.assertEqual(shortcut_3.access_via_link, "view")
        self.assertEqual(sub_folder.access_via_link, "view")
        self.assertEqual(sub_file.access_via_link, "view")

        self.assertEqual(target.access_via_link, "none")
        self.assertEqual(shortcut.access_via_link, "none")

        root.with_user(self.internal_user).action_update_access_rights(
            partners={self.internal_user.partner_id: ("edit", None)}
        )

        def get_access(document):
            return document.access_ids.filtered(
                lambda a: a.partner_id == self.internal_user.partner_id
            ).role

        self.assertEqual(get_access(root), "edit")
        self.assertEqual(get_access(file_1), "edit")
        self.assertEqual(
            get_access(file_2), False, "The user can not write on that document"
        )
        self.assertEqual(get_access(file_3), False)
        self.assertEqual(get_access(sub_folder), "edit")
        self.assertEqual(get_access(sub_file), "edit")

        self.assertEqual(get_access(shortcut_1), "edit")
        self.assertEqual(get_access(shortcut_2), False)
        self.assertEqual(get_access(shortcut_3), False)

        self.assertEqual(get_access(target), False)
        self.assertEqual(get_access(shortcut), False)

    def test_shortcuts_cant_have_children(self):
        folder_a_shortcut = self.folder_a.action_create_shortcut()
        with self.assertRaises(ValidationError):
            self.env["document.document"].create(
                {"type": "folder", "folder_id": folder_a_shortcut.id}
            )
        self.folder_b.folder_id = folder_a_shortcut
        self.assertEqual(
            self.folder_b.folder_id,
            self.folder_a,
            "The shortcut's target should have been used",
        )

    def test_portal_cant_own_root_documents(self):
        self.assertFalse(self.folder_a.folder_id)
        with self.assertRaises(UserError):
            self.folder_a.owner_id = self.portal_user

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_copy_document_access(self):
        IN_ONE_DAY = fields.Datetime.now() + datetime.timedelta(days=1)
        documents = self.document_gif | self.document_txt

        self.folder_b.access_internal = "none"
        self.folder_b.action_update_access_rights(
            partners={self.internal_user.partner_id: ("view", False)}
        )

        copied_document = documents.with_user(self.internal_user).copy()
        self.assertFalse(copied_document.folder_id)
        self.assertEqual(copied_document.owner_id, self.internal_user)

        self.folder_b.action_update_access_rights(
            partners={self.internal_user.partner_id: ("edit", False)}
        )
        self.document_gif.action_update_access_rights(
            partners={self.internal_user.partner_id: (False, False)}
        )
        self.document_gif.access_internal = "none"
        with self.assertRaises(AccessError, msg="No access to one of the document"):
            documents.with_user(self.internal_user).copy()

        self.document_txt.action_update_access_rights(
            partners={self.portal_user.partner_id: ("view", IN_ONE_DAY)}
        )
        self.document_gif.action_update_access_rights(
            partners={self.internal_user.partner_id: ("view", False)}
        )
        (documents | self.folder_b).with_user(self.internal_user).copy()

        gif_copy, txt_copy = documents.with_user(self.internal_user).copy()
        self.assertEqual((gif_copy | txt_copy).owner_id, self.internal_user)
        self.assertTrue(gif_copy.attachment_id)
        gif_copy_access_ids = gif_copy.access_ids
        self.assertEqual(
            {(a.partner_id.name, a.role) for a in gif_copy_access_ids},
            {(self.internal_user.name, False), (self.doc_user.name, "edit")},
            "Existing member and original owner should have access",
        )
        self.assertSetEqual({*gif_copy_access_ids.mapped("expiration_date")}, {False})
        txt_copy_access_by_partner = {
            a.partner_id: (a.role, a.expiration_date) for a in txt_copy.access_ids
        }
        self.assertEqual(len(txt_copy_access_by_partner), 3)
        self.assertEqual(
            txt_copy_access_by_partner.get(self.portal_user.partner_id),
            ("view", IN_ONE_DAY),
        )
        self.assertEqual(
            txt_copy_access_by_partner.get(self.doc_user.partner_id), ("edit", False)
        )
        self.assertEqual(
            txt_copy_access_by_partner.get(self.internal_user.partner_id),
            (False, False),
        )

        self.document_txt.action_archive()
        with self.assertRaises(UserError, msg="Cannot copy document in the Trash"):
            documents.with_user(self.internal_user).copy()

        url_document_in_my_folder = self.env["document.document"].create(
            {
                "name": "url",
                "type": "url",
                "url": "https://www.odoo.com/",
                "owner_id": self.internal_user.id,
            }
        )
        _, url_copied = (
            (self.document_gif | url_document_in_my_folder)
            .with_user(self.internal_user)
            .copy()
        )
        self.assertEqual(url_copied.owner_id, self.internal_user)

        shortcut = self.env["document.document"].create(
            {
                "name": "shortcut",
                "shortcut_document_id": self.document_gif.id,
                "owner_id": self.internal_user.id,
            }
        )

        shortcuts = url_document_in_my_folder | shortcut
        shortcuts.folder_id = self.folder_a
        with mute_logger("odoo.addons.document.models.document_document"):
            copied_shortcuts = shortcuts.copy()
        self.assertEqual(copied_shortcuts.folder_id, self.folder_a)

        self.document_gif.owner_id = self.internal_user
        copied_shortcuts = shortcuts.with_user(self.internal_user).copy()
        self.assertFalse(copied_shortcuts.folder_id)
        self.assertEqual(copied_shortcuts.owner_id, self.internal_user)

        self.folder_b.folder_id = self.folder_a
        for access in ("edit", "view"):
            self.folder_b.action_update_access_rights(
                partners={self.internal_user.partner_id: (access, False)}
            )
            copied_folder = self.folder_b.with_user(self.internal_user).copy()
            self.assertFalse(copied_folder.folder_id)
            self.assertEqual(copied_folder.owner_id, self.internal_user)
            self.assertEqual(len(copied_folder.children_ids), 6)
            self.assertNotEqual(copied_folder.children_ids, self.folder_b.children_ids)

        self.folder_b.folder_id = False
        self.assertEqual(self.folder_b.owner_id, self.doc_user)
        self.assertFalse(self.folder_b._is_company_root_folder())
        copied_folder = self.folder_b.with_user(self.document_manager).copy()
        self.assertFalse(copied_folder.folder_id)
        self.assertEqual(copied_folder.owner_id, self.document_manager)

        self.folder_b.owner_id = False
        self.assertTrue(self.folder_b._is_company_root_folder())
        copied_folder = self.folder_b.with_user(self.document_manager).copy()
        self.assertFalse(copied_folder.folder_id)
        self.assertFalse(copied_folder.owner_id)

        self.folder_b.access_internal = "edit"
        copied_folder = self.folder_b.with_user(self.internal_user).copy()
        self.assertFalse(copied_folder.folder_id)
        self.assertEqual(copied_folder.owner_id, self.internal_user)

        self.folder_b.action_update_access_rights(
            access_via_link="edit",
            partners={self.portal_user.partner_id: ("edit", False)},
        )
        with self.assertRaises(ValidationError):
            self.folder_b.with_user(self.portal_user).copy()

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_deleting_in_non_edit_folder(self):
        folder = (
            self.env["document.document"]
            .with_user(self.document_manager)
            .create(
                {
                    "folder_id": False,
                    "name": "Folder with User",
                    "type": "folder",
                    "access_ids": [
                        Command.create(
                            {"partner_id": self.doc_user.partner_id.id, "role": "edit"}
                        )
                    ],
                }
            )
        )
        user_doc_1, user_doc_2 = user_docs = (
            self.env["document.document"]
            .with_user(self.doc_user)
            .create(
                [
                    {
                        "folder_id": folder.id,
                        "name": f"User doc #{idx}",
                        "type": "binary",
                    }
                    for idx in range(2)
                ]
            )
        )
        self.assertEqual(user_docs.owner_id, self.doc_user)
        folder.with_user(self.document_manager).action_update_access_rights(
            partners={self.doc_user.partner_id: (False, None)},
        )
        self.assertEqual(folder.with_user(self.doc_user).user_permission, "none")
        user_doc_1.with_user(self.doc_user).action_archive()
        self.assertFalse(
            user_doc_1.active, "Owner should be able to archive the document"
        )
        user_doc_1.with_user(self.doc_user).action_unarchive()
        self.assertTrue(
            user_doc_1.active, "Owner should be able to restore the document"
        )
        user_doc_1.with_user(self.doc_user).unlink()
        self.assertFalse(
            user_doc_1.exists(), "Owner should be able to unlink the document"
        )

        user_doc_2.with_user(self.document_manager).owner_id = self.document_manager
        user_doc_2.with_user(self.document_manager).action_update_access_rights(
            partners={self.doc_user.partner_id: ("edit", None)},
        )
        self.assertEqual(user_doc_2.with_user(self.doc_user).user_permission, "edit")
        with self.assertRaises(
            UserError,
            msg="Editor without edit permission on folder shouldn't be able to archive",
        ):
            user_doc_2.with_user(self.doc_user).action_archive()
        with self.assertRaises(
            UserError,
            msg="Editor without edit permission on folder shouldn't be able to delete",
        ):
            user_doc_2.with_user(self.doc_user).unlink()

        user_doc_2.folder_id.sudo().access_internal = "none"
        with self.assertRaises(
            UserError,
            msg="Editor with no permission on folder shouldn't be able to delete",
        ):
            user_doc_2.with_user(self.doc_user).unlink()

        user_doc_2.folder_id.sudo().access_internal = "view"
        with self.assertRaises(
            UserError,
            msg="Editor with view permission on folder shouldn't be able to delete",
        ):
            user_doc_2.with_user(self.doc_user).unlink()

    def test_updating_owner(self):
        self.assertEqual(self.folder_a_a.owner_id, self.doc_user)
        self.folder_a.action_update_access_rights(access_internal="edit")
        self.assertEqual(
            self.folder_a_a.with_user(self.internal_user).user_permission, "edit"
        )

        with self.assertRaises(AccessError):
            self.folder_a_a.with_user(self.internal_user).owner_id = self.internal_user

        self.folder_a_a.action_update_access_rights(access_internal="none")
        self.assertEqual(
            self.folder_a_a.with_user(self.internal_user).user_permission, "none"
        )

        self.document_txt.folder_id = self.folder_a_a
        self.document_txt.owner_id = self.document_manager
        self.document_txt.action_update_access_rights(
            partners={self.doc_user.partner_id: ("view", False)}
        )

        self.assertEqual(
            self.document_txt.with_user(self.doc_user).user_permission, "view"
        )

        self.folder_a_a.with_user(self.doc_user).owner_id = self.internal_user
        self.assertEqual(
            self.folder_a_a.with_user(self.doc_user).user_permission,
            "edit",
            "Previous owner should have kept edit permission on folder",
        )

        self.assertEqual(
            self.document_txt.with_user(self.doc_user).user_permission,
            "view",
            "Previous owner should not have gained rights on folder content",
        )

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_embedded_action(self):
        self.folder_a.action_update_access_rights(
            access_internal="edit",
            partners={self.portal_user.partner_id: ("edit", False)},
        )
        with self.assertRaises(AccessError):
            self.env["document.document"].with_user(
                self.internal_user
            ).action_folder_embed_action(self.folder_a.id, self.server_action.id)
        self.server_action.group_ids = self.env.ref("document.group_documents_manager")
        with self.assertRaises(UserError):
            self.env["document.document"].with_user(
                self.doc_user
            ).action_folder_embed_action(self.folder_a.id, self.server_action.id)
        self.server_action.group_ids = self.env.ref("base.group_user")
        self.env["document.document"].with_user(
            self.doc_user
        ).action_folder_embed_action(self.folder_a.id, self.server_action.id)
        doc = self.env["document.document"].create(
            {"name": "A request", "folder_id": self.folder_a.id}
        )
        embedded_action = doc.available_embedded_actions_ids
        self.assertEqual(len(embedded_action), 1)
        doc_in_context = self.env["document.document"].with_context(
            active_model="document.document", active_id=doc.id
        )

        with self.assertRaises(AccessError):
            doc_in_context.with_user(self.portal_user).action_execute_embedded_action(
                embedded_action.id
            )
        doc_in_context.with_user(self.internal_user).action_execute_embedded_action(
            embedded_action.id
        )

        with self.assertRaises(UserError):
            doc_in_context.with_context(
                active_ids=(doc | self.folder_a).ids,
            ).with_user(self.internal_user).action_execute_embedded_action(
                embedded_action.id
            )
        doc.action_update_access_rights(access_internal="none")

        with self.assertRaises(AccessError):
            doc_in_context.with_context(active_id=doc.id).with_user(
                self.internal_user
            ).action_execute_embedded_action(embedded_action.id)

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_embedded_action_shortcut_folder(self):
        self.folder_a.action_update_access_rights(
            access_internal="edit",
            partners={self.portal_user.partner_id: ("edit", False)},
        )
        doc = self.env["document.document"].create(
            {"name": "A request", "folder_id": self.folder_a.id}
        )
        self.assertFalse(doc.available_embedded_actions_ids)
        folder_a_shortcut = self.folder_a.action_create_shortcut()
        self.assertFalse(
            self.folder_a._get_folder_embedded_actions([self.folder_a.id]).get(
                self.folder_a.id
            )
        )
        self.assertFalse(
            self.folder_a._get_folder_embedded_actions([folder_a_shortcut.id]).get(
                folder_a_shortcut.id
            )
        )

        with self.assertRaises(AccessError):
            self.env["document.document"].with_user(
                self.internal_user
            ).action_folder_embed_action(folder_a_shortcut.id, self.server_action.id)
        self.server_action.group_ids = self.env.ref("document.group_documents_manager")
        with self.assertRaises(UserError):
            self.env["document.document"].with_user(
                self.doc_user
            ).action_folder_embed_action(folder_a_shortcut.id, self.server_action.id)
        self.server_action.group_ids = self.env.ref("base.group_user")
        self.env["document.document"].with_user(
            self.doc_user
        ).action_folder_embed_action(folder_a_shortcut.id, self.server_action.id)

        self.assertEqual(len(doc.available_embedded_actions_ids), 1)
        self.assertTrue(
            self.folder_a._get_folder_embedded_actions([self.folder_a.id])[
                self.folder_a.id
            ]
        )
        self.assertEqual(
            self.folder_a._get_folder_embedded_actions([folder_a_shortcut.id])[
                folder_a_shortcut.id
            ],
            self.folder_a._get_folder_embedded_actions([self.folder_a.id])[
                self.folder_a.id
            ],
        )

        self.folder_a.action_update_access_rights(access_internal="view")
        self.internal_user.group_ids |= self.env.ref("document.group_documents_user")
        document = self.document_gif.with_user(self.internal_user)
        document.sudo().access_internal = "edit"

        action = (
            self.env["ir.actions.server"]
            .create(
                {
                    "name": "Test Action",
                    "model_id": self.env["ir.model"]._get_id("document.document"),
                    "update_path": "folder_id",
                    "usage": "documents_embedded",
                    "state": "object_write",
                    "resource_ref": f"document.document,{self.folder_a.id}",
                }
            )
            .with_user(self.internal_user)
        )

        self.assertEqual(document.folder_id.user_permission, "view")
        with self.assertRaises(AccessError):
            document.env["document.document"].action_folder_embed_action(
                document.folder_id.id, action.id
            )

        document.folder_id.sudo().access_internal = "edit"
        with RecordCapturer(self.env["ir.embedded.actions"], []) as capturer:
            document.env["document.document"].action_folder_embed_action(
                document.folder_id.id, action.id
            )
            embedded = capturer.records
        self.assertEqual(len(embedded), 1)

        self.assertEqual(
            self.folder_a.with_user(self.internal_user).user_permission, "view"
        )
        self.assertEqual(
            self.folder_b.with_user(self.internal_user).user_permission, "edit"
        )
        with self.assertRaises(AccessError):
            embedded.with_user(self.internal_user).parent_res_id = self.folder_a.id

        embedded.parent_res_id = self.folder_a.id
        with self.assertRaises(AccessError):
            embedded.with_user(self.internal_user).parent_res_id = self.folder_b.id

    def test_groupless_embedded_action_availability(self):
        embedded_action = self.env["ir.embedded.actions"].create(
            {
                "name": "public action",
                "parent_action_id": self.env.ref("document.document_action").id,
                "action_id": self.server_action.id,
                "parent_res_model": "document.document",
                "group_ids": [Command.clear()],
                "parent_res_id": self.document_txt.folder_id.id,
            }
        )
        self.assertIn(embedded_action, self.document_txt.available_embedded_actions_ids)

    @freeze_time("2025-02-26 15:02:00")
    def test_log_owner_access_when_passing_access_ids(self):
        doc = (
            self.env["document.document"]
            .with_user(self.doc_user)
            .create(
                {
                    "access_ids": [
                        Command.create(
                            {
                                "partner_id": self.document_manager.partner_id.id,
                                "role": "edit",
                            }
                        )
                    ]
                }
            )
        )
        self.assertEqual(
            set(
                doc.access_ids.mapped(
                    lambda a: (a.partner_id, a.role, a.last_access_date)
                )
            ),
            {
                (self.document_manager.partner_id, "edit", False),
                (self.doc_user.partner_id, False, fields.Datetime.now()),
            },
        )
        doc = (
            self.env["document.document"]
            .with_user(self.doc_user)
            .create({"access_ids": False})
        )
        self.assertEqual(
            set(
                doc.access_ids.mapped(
                    lambda a: (a.partner_id, a.role, a.last_access_date)
                )
            ),
            {(self.doc_user.partner_id, False, fields.Datetime.now())},
        )

    @users("documents@example.com")
    def test_embedded_actions_unembed(self):
        folder = self.document_txt.folder_id
        self.assertFalse(self.document_txt.available_embedded_actions_ids)
        self.document_txt.invalidate_recordset(["available_embedded_actions_ids"])
        embedded_action_vals = {
            "name": "public action",
            "parent_action_id": self.env.ref("document.document_action").id,
            "action_id": self.server_action.id,
            "parent_res_model": "document.document",
            "parent_res_id": folder.id,
        }
        embedded_action_with_group = self.env["ir.embedded.actions"].create(
            {
                **embedded_action_vals,
                "group_ids": [self.env.ref("document.group_documents_manager").id],
            }
        )
        self.assertIn(
            embedded_action_with_group, self.document_txt.available_embedded_actions_ids
        )
        self.document_txt.invalidate_recordset(["available_embedded_actions_ids"])
        self.env["document.document"].action_folder_embed_action(
            folder.id, self.server_action.id
        )
        self.assertFalse(
            self.document_txt.available_embedded_actions_ids,
            "Embedded action with group should have been removed.",
        )
        self.document_txt.invalidate_recordset(["available_embedded_actions_ids"])
        self.env["document.document"].action_folder_embed_action(
            folder.id, self.server_action.id
        )
        self.assertTrue(
            self.document_txt.available_embedded_actions_ids,
            "Embedded action should have been created.",
        )
        self.document_txt.available_embedded_actions_ids.group_ids = False
        self.env["document.document"].action_folder_embed_action(
            folder.id, self.server_action.id
        )
        self.assertFalse(
            self.document_txt.available_embedded_actions_ids,
            "Embedded action without group should have been removed.",
        )
        self.document_txt.invalidate_recordset(["available_embedded_actions_ids"])

        self.env["ir.embedded.actions"].create(
            [
                {
                    **embedded_action_vals,
                    "group_ids": [self.env.ref("document.group_documents_manager").id],
                },
                embedded_action_vals,
            ]
        )
        self.assertTrue(self.document_txt.available_embedded_actions_ids)
        self.document_txt.invalidate_recordset(["available_embedded_actions_ids"])

        self.env["document.document"].action_folder_embed_action(
            folder.id, self.server_action.id
        )
        self.assertFalse(
            self.document_txt.available_embedded_actions_ids,
            "Embedded action with and without group should have been removed.",
        )

    def test_restricted_folder_dependant_fields(self):
        self.folder_b.access_internal = "none"
        self.assertEqual(
            self.folder_b.with_user(self.internal_user).user_permission, "none"
        )
        self.assertFalse(
            self.env["document.document"]
            .with_user(self.internal_user)
            ._get_folder_embedded_actions(self.folder_b.id)
        )
        self.document_gif.access_internal = "view"
        self.assertEqual(
            self.document_gif.with_user(self.internal_user).user_permission, "view"
        )

        self.document_gif.invalidate_recordset()
        self.assertFalse(
            self.document_gif.with_user(
                self.internal_user
            ).available_embedded_actions_ids
        )

        self.env["document.document"].with_user(
            self.internal_user
        )._get_folder_embedded_actions(self.folder_b.id)
        with self.assertRaises(UserError):
            self.env["document.document"].with_user(
                self.internal_user
            ).get_documents_actions(self.folder_b.id)

        folder_b_embedded_server_action_ids = {
            server_action["id"]
            for server_action in self.folder_b.action_folder_embed_action(
                self.folder_b.id, self.server_action.id
            )
            if server_action["is_embedded"]
        }
        embedded_action_folder_b = self.document_gif.with_user(
            self.internal_user
        ).available_embedded_actions_ids
        self.assertIn(
            embedded_action_folder_b.action_id.id, folder_b_embedded_server_action_ids
        )

    def test_tracking_creation_on_access_rights_changes(self):
        self.folder_a_a.unlink()
        sub_folder_ids = self.env["document.document"].create(
            [
                {
                    "type": "folder",
                    "name": f"sub folder A-{letter}",
                    "folder_id": self.folder_a.id,
                }
                for letter in ("A", "B", "C", "D", "E", "F", "G", "H", "I", "j")
            ]
        )
        for sub_folder in sub_folder_ids:
            self.env["document.document"].create(
                [
                    {
                        "type": "folder",
                        "name": f"{sub_folder.name}-{count}",
                        "folder_id": sub_folder.id,
                        "children_ids": [
                            Command.create(
                                {
                                    "name": f"File {count}",
                                }
                            )
                            for count in range(10)
                        ],
                    }
                    for count in range(10)
                ]
            )
        self.assertEqual(len(self.folder_a.children_ids), 10)
        for child in self.folder_a.children_ids:
            self.assertEqual(len(child.children_ids), 10)

        self.assertEqual(self.folder_a.access_internal, "view")

        def _get_mail_messages(doc_ids):
            return self.env["mail.message"].search(
                [("res_id", "in", doc_ids), ("tracking_value_ids", "!=", False)]
            )

        folder_a_d = sub_folder_ids[3]
        self.assertEqual(folder_a_d.access_internal, "view")
        folder_a_d.action_update_access_rights(
            access_internal="edit",
            partners={self.portal_user.partner_id.id: ("view", False)},
        )

        with self.enter_registry_test_mode():
            self.env.ref(
                "document.ir_cron_documents_access_tracking"
            ).method_direct_trigger()

        folder_a_d_message_ids = _get_mail_messages(
            folder_a_d.ids + folder_a_d.children_ids.ids
        )
        self.assertTrue(folder_a_d_message_ids.exists())
        for message in folder_a_d_message_ids:
            self.assertTracking(
                message, [("access_internal", "char", "Viewer", "Editor")], strict=True
            )
            self.assertIn(
                "Portal user has gained access as Viewer",
                " ".join(html2plaintext(message.body).split()),
            )

        self.folder_a.action_update_access_rights(
            access_internal="edit",
            access_via_link="view",
            is_access_via_link_hidden=True,
            partners={self.portal_user.partner_id.id: ("edit", False)},
        )

        while self.env["document.access.tracking"].search_count([]) > 0:
            with self.enter_registry_test_mode():
                self.env.ref(
                    "document.ir_cron_documents_access_tracking"
                ).method_direct_trigger()

        other_folders_ids = sub_folder_ids - folder_a_d
        message_ids = _get_mail_messages(
            other_folders_ids.ids + other_folders_ids.children_ids.ids
        )
        self.assertTrue(message_ids.exists())
        for message in message_ids:
            self.assertTracking(
                message,
                [
                    ("access_internal", "char", "Viewer", "Editor"),
                    ("access_via_link", "char", "None", "Viewer"),
                ],
                strict=True,
            )
            self.assertIn(
                "Portal user has gained access as Editor",
                " ".join(html2plaintext(message.body).split()),
            )

        folder_a_d_latest_message_ids = _get_mail_messages(
            folder_a_d.ids + folder_a_d.children_ids.ids
        ).filtered(lambda message: message.id not in folder_a_d_message_ids.ids)
        for message in folder_a_d_latest_message_ids:
            self.assertTracking(
                message,
                [
                    ("access_via_link", "char", "None", "Viewer"),
                ],
                strict=True,
            )
            self.assertIn(
                "Portal user rights changed from Viewer to Editor",
                " ".join(html2plaintext(message.body).split()),
            )

    def test_members_access_on_move_documents(self):
        self.document_txt.action_update_access_rights(
            partners={self.internal_user.partner_id.id: ("view", False)}
        )
        self.env["document.access"].create(
            {
                "document_id": self.folder_a.id,
                "partner_id": self.internal_user.partner_id.id,
                "last_access_date": fields.Datetime.now(),
            }
        )
        self.assertIn(
            (self.internal_user.partner_id, "view"),
            self.document_txt.access_ids.mapped(lambda a: (a.partner_id, a.role)),
        )
        self.assertIn(
            (self.internal_user.partner_id, False),
            self.folder_a.access_ids.mapped(lambda a: (a.partner_id, a.role)),
        )

        self.document_txt.folder_id = self.folder_a.id
        self.assertIn(
            (self.internal_user.partner_id, "view"),
            self.document_txt.access_ids.mapped(lambda a: (a.partner_id, a.role)),
        )

    def test_members_invitation(self):
        Access = self.env["document.access"]
        internal_access = Access.create(
            {
                "document_id": self.folder_a.id,
                "partner_id": self.internal_user.partner_id.id,
                "last_access_date": fields.Datetime.now(),
                "role": "view",
            }
        )
        with self.assertRaises(UserError):
            internal_access._get_member_signup_token()

        portal_access = Access.create(
            {
                "document_id": self.folder_a.id,
                "partner_id": self.portal_user.partner_id.id,
                "last_access_date": fields.Datetime.now(),
                "role": "view",
            }
        )
        with self.assertRaises(UserError):
            portal_access._get_member_signup_token()

        public_access = Access.create(
            {
                "document_id": self.folder_a.id,
                "partner_id": self.env["res.partner"].create({"name": "Test"}).id,
                "last_access_date": fields.Datetime.now(),
                "role": "view",
            }
        )
        token = public_access._get_member_signup_token()
        self.assertEqual(
            Access._get_member_from_token(public_access.id, token), public_access
        )
        self.assertNotEqual(
            Access._get_member_from_token(public_access.id, "invalid" + token),
            public_access,
        )

        public_access.expiration_date = fields.Datetime.now() + datetime.timedelta(
            days=1
        )
        token = public_access._get_member_signup_token()
        self.assertEqual(
            Access._get_member_from_token(public_access.id, token), public_access
        )

        token = public_access._get_member_signup_token()
        public_access.expiration_date = fields.Datetime.now() - datetime.timedelta(
            days=1
        )
        self.assertFalse(Access._get_member_from_token(public_access.id, token))

        public_access = Access.create(
            {
                "document_id": self.folder_a.id,
                "partner_id": self.env["res.partner"].create({"name": "Test"}).id,
                "last_access_date": fields.Datetime.now(),
            }
        )
        with self.assertRaises(UserError):
            public_access._get_member_signup_token()

    def test_permissions_internal_propagation_on_folder_moves(self):
        not_secret_folder = self.env["document.document"].create(
            {
                "name": "Not Secret Folder",
                "type": "folder",
                "access_internal": "edit",
                "children_ids": [
                    Command.create(
                        {
                            "name": "Secret Folder",
                            "type": "folder",
                            "access_internal": "none",
                        }
                    ),
                ],
                "owner_id": self.document_manager.id,
            }
        )
        secret_folder = not_secret_folder.children_ids[0]
        self.assertEqual(
            secret_folder.with_user(self.internal_user).user_permission, "none"
        )
        none = (
            self.env["document.document"]
            .with_user(self.internal_user)
            .create(
                {
                    "name": "none",
                    "type": "folder",
                    "access_internal": "none",
                }
            )
        )
        editor = (
            self.env["document.document"]
            .with_user(self.internal_user)
            .create(
                {
                    "name": "editor",
                    "type": "folder",
                    "access_internal": "edit",
                }
            )
        )

        not_secret_folder.with_user(self.internal_user).action_move_folder(
            target=str(none.id)
        )
        none.with_user(self.internal_user).action_move_folder(target=str(editor.id))
        with self.assertRaises(AccessError):
            secret_folder.with_user(self.internal_user).check_access("read")
        self.assertEqual(secret_folder.access_internal, "none")

    def test_permissions_member_and_owner_propagation_on_folder_moves(self):
        member_folder = self.env["document.document"].create(
            {
                "name": "Member Folder",
                "type": "folder",
                "access_internal": "none",
                "children_ids": [
                    Command.create(
                        {
                            "name": "Secret Folder",
                            "type": "folder",
                            "access_internal": "none",
                            "access_ids": False,
                        }
                    ),
                ],
                "access_ids": [
                    Command.create(
                        {"partner_id": self.internal_user.partner_id.id, "role": "edit"}
                    )
                ],
                "owner_id": self.document_manager.id,
            }
        )
        secret_folder = member_folder.children_ids[0]
        self.assertEqual(secret_folder.with_user(self.doc_user).user_permission, "none")
        none = (
            self.env["document.document"]
            .with_user(self.internal_user)
            .create(
                {
                    "name": "none",
                    "type": "folder",
                    "access_internal": "none",
                }
            )
        )
        doc_user_editor = (
            self.env["document.document"]
            .with_user(self.internal_user)
            .create(
                {
                    "name": "editor",
                    "type": "folder",
                    "access_internal": "none",
                    "access_ids": [
                        Command.create(
                            {"partner_id": self.doc_user.partner_id.id, "role": "edit"}
                        )
                    ],
                }
            )
        )

        member_folder.with_user(self.internal_user).action_move_folder(
            target=str(none.id)
        )
        none.with_user(self.internal_user).action_move_folder(
            target=str(doc_user_editor.id)
        )

        none.with_user(self.doc_user).check_access("read")
        member_folder.with_user(self.doc_user).check_access("read")
        self.assertIn(self.doc_user.partner_id, member_folder.access_ids.partner_id)

        with self.assertRaises(AccessError):
            secret_folder.with_user(self.internal_user).check_access("read")
        with self.assertRaises(AccessError):
            secret_folder.with_user(self.doc_user).check_access("read")

        self.assertNotIn(
            self.internal_user.partner_id, secret_folder.access_ids.partner_id
        )
        self.assertNotIn(self.doc_user.partner_id, secret_folder.access_ids.partner_id)
