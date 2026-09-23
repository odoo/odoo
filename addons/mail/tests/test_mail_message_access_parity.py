import contextlib

from odoo.exceptions import AccessError
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store


@tagged("post_install", "-at_install")
class TestMailMessageAccessParity(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()
        Message = cls.env["mail.message"].sudo()
        cls.doc = cls.env["res.partner"].create({"name": "Parity document"})
        cls.other_partner = cls.user_admin.partner_id
        cls.emp_partner = cls.user_employee.partner_id
        cls.portal_partner = cls.user_portal.partner_id
        comment = cls.env.ref("mail.mt_comment").id
        note = cls.env.ref("mail.mt_note").id

        def make(**vals):
            base = {
                "body": "<p>b</p>",
                "message_type": "comment",
                "subtype_id": comment,
                "model": "res.partner",
                "res_id": cls.doc.id,
                "author_id": cls.other_partner.id,
            }
            return Message.create({**base, **vals})

        cls.messages_by_shape = {
            "own_author": make(author_id=cls.emp_partner.id),
            "recipient": make(
                partner_ids=[(6, 0, [cls.emp_partner.id, cls.portal_partner.id])]
            ),
            "doc_readable": make(),
            "private": make(model=False, res_id=False),
            "user_notification": make(message_type="user_notification"),
            "internal_flag": make(is_internal=True),
            "internal_subtype": make(subtype_id=note),
            "no_subtype": make(subtype_id=False),
            "notification_type": make(message_type="notification"),
        }

        notified = make()
        cls.env["mail.notification"].sudo().create(
            {
                "mail_message_id": notified.id,
                "res_partner_id": cls.emp_partner.id,
                "notification_type": "inbox",
            }
        )
        cls.messages_by_shape["notified"] = notified

        unknown_model = make()
        cls.env.flush_all()
        cls.env.cr.execute(
            "UPDATE mail_message SET model='no.such.model', res_id=7 WHERE id=%s",
            (unknown_model.id,),
        )
        cls.env.invalidate_all()
        cls.messages_by_shape["unknown_model"] = unknown_model

        cls.all_ids = sorted(m.id for m in cls.messages_by_shape.values())
        cls.shape_by_id = {m.id: name for name, m in cls.messages_by_shape.items()}

    def _shapes(self, ids):
        return sorted(self.shape_by_id[i] for i in ids)

    @mute_logger("odoo.addons.base.models.ir_access")
    def test_search_and_check_access_agree_per_user(self):
        for user in (
            self.user_admin,
            self.user_employee,
            self.user_portal,
            self.env.ref("base.public_user"),
        ):
            with self.subTest(user=user.login):
                Message = self.env["mail.message"].with_user(user)
                self.env.invalidate_all()
                searched = set(Message.search([("id", "in", self.all_ids)]).ids)
                self.env.invalidate_all()
                filtered = set(
                    Message.browse(self.all_ids)._filtered_access("read").ids
                )
                self.env.invalidate_all()
                one_by_one = {
                    mid
                    for mid in self.all_ids
                    if Message.browse(mid).has_access("read")
                }
                self.assertEqual(
                    self._shapes(searched),
                    self._shapes(filtered),
                    "search and _filtered_access must return the same messages",
                )
                self.assertEqual(
                    self._shapes(searched),
                    self._shapes(one_by_one),
                    "search and per-record has_access must return the same messages",
                )

    @mute_logger("odoo.addons.base.models.ir_access")
    def test_internal_only_shapes_stay_hidden_from_portal(self):
        Message = self.env["mail.message"].with_user(self.user_portal)
        self.env.invalidate_all()
        visible = self._shapes(Message.search([("id", "in", self.all_ids)]).ids)
        self.assertEqual(visible, ["recipient"])


@tagged("post_install", "-at_install")
class TestMailMessageSearchFlush(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc = cls.env["res.partner"].create({"name": "Flush document"})
        cls.message = (
            cls.env["mail.message"]
            .sudo()
            .create(
                {
                    "author_id": cls.user_employee.partner_id.id,
                    "body": "<p>b</p>",
                    "message_type": "comment",
                    "model": "res.partner",
                    "res_id": cls.doc.id,
                    "subject": "before",
                    "subtype_id": cls.env.ref("mail.mt_comment").id,
                }
            )
        )
        cls.env.flush_all()

    def _as_employee(self):
        return self.env["mail.message"].with_user(self.user_employee)

    def test_search_sees_a_field_written_in_the_same_transaction(self):
        self.message.sudo().subject = "after"
        Message = self._as_employee()
        self.assertEqual(
            Message.search(
                [("id", "=", self.message.id), ("subject", "=", "after")]
            ).ids,
            [self.message.id],
        )
        self.assertFalse(
            Message.search([("id", "=", self.message.id), ("subject", "=", "before")])
        )

    def test_search_count_sees_a_field_written_in_the_same_transaction(self):
        self.message.sudo().subject = "counted"
        self.assertEqual(
            self._as_employee().search_count(
                [("id", "=", self.message.id), ("subject", "=", "counted")]
            ),
            1,
        )

    def test_search_fetch_sees_a_field_written_in_the_same_transaction(self):
        self.message.sudo().subject = "fetched"
        self.assertEqual(
            self._as_employee()
            .search_fetch(
                [("id", "=", self.message.id), ("subject", "=", "fetched")], ["id"]
            )
            .ids,
            [self.message.id],
        )


@tagged("post_install", "-at_install")
class TestMailMessageInternalFlush(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()
        cls.doc = cls.env["res.partner"].create({"name": "Internal document"})
        cls.message = (
            cls.env["mail.message"]
            .sudo()
            .create(
                {
                    "author_id": cls.user_admin.partner_id.id,
                    "body": "<p>b</p>",
                    "is_internal": False,
                    "message_type": "comment",
                    "model": "res.partner",
                    "partner_ids": [(6, 0, [cls.user_portal.partner_id.id])],
                    "res_id": cls.doc.id,
                    "subtype_id": cls.env.ref("mail.mt_comment").id,
                }
            )
        )
        cls.env.flush_all()

    def _portal_view(self):
        return (
            self.env["mail.message"].with_user(self.user_portal).browse(self.message.id)
        )

    def test_turning_internal_hides_it_before_the_flush(self):
        self.env.invalidate_all()
        self.assertTrue(self._portal_view().has_access("read"))
        self.message.sudo().write({"is_internal": True})
        self.assertFalse(
            self._portal_view().has_access("read"),
            "a message turned internal must be hidden by the very next check",
        )

    def test_clearing_internal_reveals_it_before_the_flush(self):
        self.message.sudo().write({"is_internal": True})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(self._portal_view().has_access("read"))
        self.message.sudo().write({"is_internal": False})
        self.assertTrue(self._portal_view().has_access("read"))


@tagged("post_install", "-at_install")
class TestMailMessageCreateDetails(MailCommon):
    def test_mail_thread_model_with_a_res_id_does_not_raise(self):
        message = (
            self.env["mail.message"]
            .sudo()
            .create(
                {
                    "body": "<p>b</p>",
                    "message_type": "comment",
                    "model": "mixin.mail.thread",
                    "res_id": 5,
                }
            )
        )
        self.assertTrue(message)

    def test_reply_to_batch_matches_the_per_record_resolution(self):
        Message = self.env["mail.message"].sudo()
        docs = self.env["res.partner"].create(
            [{"name": "batch doc %s" % i} for i in range(4)]
        )
        authors = self.env["res.partner"].create(
            [
                {"name": "Author %s" % i, "email": "a%s@example.com" % i}
                for i in range(3)
            ]
        )
        self.env.flush_all()
        vals_list = (
            [
                {
                    "author_id": authors[index % 3].id,
                    "body": "b",
                    "message_type": "comment",
                    "model": "res.partner",
                    "res_id": docs[index % 4].id,
                }
                for index in range(12)
            ]
            + [
                {
                    "author_id": author.id,
                    "body": "b",
                    "message_type": "comment",
                    "model": "res.partner",
                    "res_id": docs[0].id,
                }
                for author in authors
            ]
            + [
                {"author_id": authors[0].id, "body": "b", "message_type": "comment"},
                {
                    "author_id": authors[1].id,
                    "body": "b",
                    "message_type": "comment",
                    "model": "res.partner",
                    "res_id": False,
                },
                {
                    "body": "b",
                    "message_type": "comment",
                    "model": "mixin.mail.thread",
                    "res_id": 9,
                },
            ]
        )
        self.env.invalidate_all()
        one_by_one = [Message._get_reply_to(dict(vals)) for vals in vals_list]
        self.env.invalidate_all()
        batched = Message._get_reply_to_batch([dict(vals) for vals in vals_list])
        self.assertEqual(batched, one_by_one)

    def test_create_does_not_scale_per_record_in_reply_to(self):
        Message = self.env["mail.message"].sudo()
        docs = self.env["res.partner"].create(
            [{"name": "scale doc %s" % i} for i in range(20)]
        )
        self.env.flush_all()

        def create(count):
            return [
                {
                    "body": "<p>b</p>",
                    "message_type": "comment",
                    "model": "res.partner",
                    "res_id": docs[index].id,
                }
                for index in range(count)
            ]

        self.env.invalidate_all()
        Message.create(create(1))
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        Message.create(create(1))
        self.env.flush_all()
        one = self.env.cr.sql_statement_count - before
        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        Message.create(create(20))
        self.env.flush_all()
        twenty = self.env.cr.sql_statement_count - before
        self.assertLess(
            twenty,
            one * 3,
            "creating 20 messages must not cost a reply-to resolution each: "
            "got %s queries for 20 against %s for 1" % (twenty, one),
        )


@tagged("post_install", "-at_install")
class TestMailMessageFetchCursors(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc = cls.env["res.partner"].create({"name": "Cursor document"})
        cls.messages = (
            cls.env["mail.message"]
            .sudo()
            .create(
                [
                    {
                        "author_id": cls.user_employee.partner_id.id,
                        "body": "<p>%s</p>" % index,
                        "message_type": "comment",
                        "model": "res.partner",
                        "res_id": cls.doc.id,
                        "subtype_id": cls.env.ref("mail.mt_comment").id,
                    }
                    for index in range(3)
                ]
            )
        )
        cls.env.flush_all()

    def _fetch(self, **kwargs):
        return (
            self.env["mail.message"]
            .with_user(self.user_employee)
            ._message_fetch(domain=[("id", "in", self.messages.ids)], **kwargs)[
                "messages"
            ]
            .ids
        )

    def test_false_cursors_mean_no_cursor_on_every_parameter(self):
        expected = self._fetch()
        self.assertEqual(len(expected), 3)
        for name in ("around", "before", "after"):
            with self.subTest(cursor=name):
                self.assertEqual(self._fetch(**{name: False}), expected)

    def test_unparseable_cursors_mean_no_cursor(self):
        expected = self._fetch()
        for name in ("around", "before", "after"):
            with self.subTest(cursor=name):
                self.assertEqual(self._fetch(**{name: "not-an-id"}), expected)

    def test_a_real_around_cursor_still_centres(self):
        self.assertEqual(
            sorted(self._fetch(around=self.messages[1].id)),
            sorted(self.messages.ids),
        )


@tagged("post_install", "-at_install")
class TestMailMessageTrackingSearch(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc = cls.env["res.partner"].create({"name": "Tracking document"})
        note = cls.env.ref("mail.mt_note").id
        Message = cls.env["mail.message"].sudo()
        cls.to_zero, cls.to_seven = Message.create(
            [
                {
                    "body": "",
                    "message_type": "notification",
                    "model": "res.partner",
                    "res_id": cls.doc.id,
                    "subtype_id": note,
                }
            ]
            * 2
        )
        field = cls.env["ir.model.fields"]._get("res.partner", "color")
        cls.env["mail.tracking.value"].sudo().create(
            [
                {
                    "field_id": field.id,
                    "mail_message_id": cls.to_zero.id,
                    "new_value_integer": 0,
                    "old_value_integer": 5,
                },
                {
                    "field_id": field.id,
                    "mail_message_id": cls.to_seven.id,
                    "new_value_integer": 7,
                    "old_value_integer": 5,
                },
            ]
        )
        cls.env.flush_all()

    def _search(self, term):
        return (
            self.env["mail.message"]
            .with_user(self.user_employee)
            ._message_fetch(domain=None, thread=self.doc, search_term=term)["messages"]
            .ids
        )

    def test_zero_is_a_value_not_an_absence(self):
        self.assertEqual(self._search("0"), [self.to_zero.id])

    def test_a_non_zero_number_still_matches_only_its_own_row(self):
        self.assertEqual(self._search("7"), [self.to_seven.id])

    def test_the_old_value_is_searchable_too(self):
        self.assertEqual(
            sorted(self._search("5")), sorted([self.to_zero.id, self.to_seven.id])
        )


@tagged("post_install", "-at_install")
class TestMailMessageWriteArguments(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()

    @users("employee")
    def test_write_does_not_mutate_the_caller_values(self):
        message = (
            self.env["mail.message"]
            .sudo()
            .create(
                {
                    "author_id": self.user_portal.partner_id.id,
                    "body": "<p>b</p>",
                    "message_type": "comment",
                }
            )
        )
        self.env.flush_all()
        vals = {"body": "<p>c</p>", "author_id": self.partner_admin.id}
        snapshot = dict(vals)
        with contextlib.suppress(AccessError):
            message.with_user(self.user_portal).write(vals)
        self.assertEqual(vals, snapshot)

    def test_a_portal_user_still_cannot_set_the_author(self):
        author = self.user_portal.partner_id
        message = (
            self.env["mail.message"]
            .sudo()
            .create(
                {
                    "author_id": author.id,
                    "body": "<p>b</p>",
                    "message_type": "comment",
                    "model": "res.partner",
                    "partner_ids": [(6, 0, [author.id])],
                    "res_id": self.user_portal.partner_id.id,
                    "subtype_id": self.env.ref("mail.mt_comment").id,
                }
            )
        )
        self.env.flush_all()
        with contextlib.suppress(AccessError):
            message.with_user(self.user_portal).write(
                {"body": "<p>c</p>", "author_id": self.partner_admin.id}
            )
        self.assertEqual(message.sudo().author_id, author)


@tagged("post_install", "-at_install")
class TestMailMessageLinkedMessages(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_portal_user()
        Message = cls.env["mail.message"].sudo()
        comment = cls.env.ref("mail.mt_comment").id
        cls.docs = cls.env["res.partner"].create(
            [{"name": "linked doc %s" % index} for index in range(20)]
        )
        cls.env.flush_all()
        cls.targets = Message.create(
            [
                {
                    "author_id": cls.user_employee.partner_id.id,
                    "body": "<p>target %s</p>" % index,
                    "message_type": "comment",
                    "model": "res.partner",
                    "res_id": cls.docs[index].id,
                    "subtype_id": comment,
                }
                for index in range(20)
            ]
        )
        cls.env.flush_all()
        cls.linkers = Message.create(
            [
                {
                    "author_id": cls.user_employee.partner_id.id,
                    "body": (
                        '<p><a class="o_message_redirect" '
                        'data-oe-model="mail.message" data-oe-id="%s">x</a></p>'
                        % cls.targets[index].id
                    ),
                    "message_type": "comment",
                    "model": "res.partner",
                    "res_id": cls.docs[index].id,
                    "subtype_id": comment,
                }
                for index in range(20)
            ]
        )
        cls.env.flush_all()

    def _store(self, messages):
        return Store().add(messages).get_result()

    def test_linked_messages_reach_the_store(self):
        messages = (
            self.env["mail.message"]
            .with_user(self.user_employee)
            .browse(self.linkers[:3].ids)
        )
        self.env.invalidate_all()
        rows = {row["id"]: row for row in self._store(messages)["mail.message"]}
        for index in range(3):
            target = self.targets[index]
            self.assertIn(target.id, rows)
            self.assertEqual(rows[target.id]["model"], "res.partner")
            self.assertEqual(rows[target.id]["res_id"], self.docs[index].id)

    def test_unreadable_link_targets_are_not_disclosed(self):
        self.targets.write({"is_internal": True})
        self.linkers[:2].write({"partner_ids": [(4, self.user_portal.partner_id.id)]})
        self.env.flush_all()
        messages = (
            self.env["mail.message"]
            .with_user(self.user_portal)
            .browse(self.linkers[:2].ids)
        )
        self.env.invalidate_all()
        rows = {row["id"] for row in self._store(messages).get("mail.message", [])}
        self.assertFalse(rows & set(self.targets.ids))

    def test_store_does_not_scale_with_the_number_of_linked_messages(self):
        Message = self.env["mail.message"].with_user(self.user_employee)
        self.env.invalidate_all()
        self._store(Message.browse(self.linkers[:2].ids))

        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        self._store(Message.browse(self.linkers[:5].ids))
        five = self.env.cr.sql_statement_count - before

        self.env.invalidate_all()
        before = self.env.cr.sql_statement_count
        self._store(Message.browse(self.linkers.ids))
        twenty = self.env.cr.sql_statement_count - before

        self.assertEqual(
            five,
            twenty,
            "serialising 20 linking messages must cost what 5 cost: "
            "got %s against %s" % (twenty, five),
        )


@tagged("post_install", "-at_install")
class TestMailMessageNotifiedParentCreate(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Message = cls.env["mail.message"].sudo()
        cls.doc = cls.env["res.partner"].create({"name": "Parent doc"})
        cls.parent = Message.create(
            {
                "body": "<p>parent</p>",
                "message_type": "comment",
                "subtype_id": cls.env.ref("mail.mt_comment").id,
                "model": "res.partner",
                "res_id": cls.doc.id,
                "author_id": cls.user_admin.partner_id.id,
            }
        )
        cls.env["mail.notification"].sudo().create(
            {
                "mail_message_id": cls.parent.id,
                "res_partner_id": cls.user_employee.partner_id.id,
                "notification_type": "inbox",
            }
        )
        foreign_res_id = cls.env["ir.cron"].sudo().search([], limit=1).id
        cls.child_same = cls._create_child_message("res.partner", cls.doc.id)
        cls.child_foreign = cls._create_child_message("ir.cron", foreign_res_id)

    @classmethod
    def _create_child_message(cls, model, res_id):
        return (
            cls.env["mail.message"]
            .sudo()
            .create(
                {
                    "body": "<p>child</p>",
                    "message_type": "comment",
                    "subtype_id": cls.env.ref("mail.mt_comment").id,
                    "parent_id": cls.parent.id,
                    "model": model,
                    "res_id": res_id,
                    "author_id": cls.user_admin.partner_id.id,
                }
            )
        )

    def _forbidden_create(self, message):
        return (
            message.with_user(self.user_employee)
            .sudo(False)
            ._get_forbidden_access("create")
        )

    def test_reply_on_the_same_document_is_granted(self):
        self.assertNotIn(
            self.child_same,
            self._forbidden_create(self.child_same),
            "a notified-parent reply on the same document must be allowed",
        )

    def test_reply_pointed_at_another_document_is_refused(self):
        self.assertIn(
            self.child_foreign,
            self._forbidden_create(self.child_foreign),
            "a notified-parent reply must not reach a foreign record",
        )
