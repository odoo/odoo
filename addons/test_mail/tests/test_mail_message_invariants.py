from markupsafe import Markup

from odoo.exceptions import MissingError
from odoo.tests.common import tagged, users

from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.tools.discuss import Store


@tagged("post_install", "-at_install")
class TestMailMessageInvariants(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.simple"].create({"name": "invariants"})

    def _post(self, **kwargs):
        kwargs.setdefault("body", "<p>b</p>")
        kwargs.setdefault("message_type", "comment")
        kwargs.setdefault("subtype_xmlid", "mail.mt_comment")
        return self.record.message_post(**kwargs)

    @users("employee")
    def test_create_does_not_query_per_record_for_the_author(self):
        Message = self.env["mail.message"]
        counts = {}
        cursor_class = type(self.env.cr)
        original_execute = cursor_class.execute
        partner_selects = []

        def spy(cr, query, params=None, log_exceptions=True):
            text = str(query)
            # a read of the partner table, not a row of another model that
            # reaches its party through a join
            if 'FROM "res_partner"' in text and text.lstrip().startswith("SELECT"):
                partner_selects.append(text)
            if params is None:
                return original_execute(cr, query)
            return original_execute(cr, query, params, log_exceptions)

        for size in (2, 12):
            partners = (
                self.env["res.partner"]
                .sudo()
                .create(
                    [
                        {
                            "name": f"A{size}-{i}",
                            "email": f"a{size}{i}@test.example.com",
                        }
                        for i in range(size)
                    ]
                )
            )
            self.env.flush_all()
            self.env.invalidate_all()
            vals_list = [
                {
                    "body": "<p>b</p>",
                    "message_type": "comment",
                    "model": "mail.test.simple",
                    "res_id": self.record.id,
                    "author_id": partner.id,
                }
                for partner in partners
            ]
            partner_selects.clear()
            self.patch(cursor_class, "execute", spy)
            try:
                messages = Message.create(vals_list)
            finally:
                self.patch(cursor_class, "execute", original_execute)
            counts[size] = len(partner_selects)
            self.assertEqual(
                [message.email_from for message in messages],
                [partner.sudo().email_formatted for partner in partners],
                "batching the author resolution must not change what it resolves",
            )
        self.assertEqual(
            counts[2],
            counts[12],
            "resolving the authors of a batch must not read res.partner once "
            f"per message: {counts}",
        )

    @users("employee")
    def test_prefetching_a_deleted_peer_does_not_fail_a_live_message(self):

        for index in range(4):
            self._post(body=f"<p>m{index}</p>")
        self.env.flush_all()
        self.env.invalidate_all()
        fetched = self.env["mail.message"].search(
            [("model", "=", "mail.test.simple"), ("res_id", "=", self.record.id)]
        )
        self.assertGreater(len(fetched), 1)
        victim_id = fetched.ids[0]
        survivor = fetched[1]
        self.assertIn(
            victim_id,
            survivor._prefetch_ids,
            "sanity: the survivor must still name the victim in its prefetch hint",
        )
        self.env["mail.message"].sudo().browse(victim_id).unlink()
        try:
            record_by_message = survivor._record_by_message()
        except MissingError:
            self.fail("a live message must serialise after a sibling is unlinked")
        self.assertEqual(record_by_message.get(survivor), self.record)
        Store().add(survivor).get_result()

    @users("employee")
    def test_message_id_and_reply_to_agree_on_the_document(self):
        Message = self.env["mail.message"].with_context(
            default_model="mail.test.simple", default_res_id=self.record.id
        )
        message = Message.create({"body": "<p>b</p>", "message_type": "comment"})
        self.assertEqual(message.model, "mail.test.simple")
        self.assertEqual(message.res_id, self.record.id)
        self.assertIn(
            f"-odoo-{self.record.id}-mail.test.simple@",
            message.message_id,
            "the document reached the message through the context, so the "
            "message-id must name it too",
        )

        private = self.env["mail.message"].create(
            {"body": "<p>b</p>", "message_type": "comment"}
        )
        self.assertIn("-odoo-private@", private.message_id)

    @users("employee")
    def test_preview_of_a_single_long_token(self):
        Message = self.env["mail.message"]
        long_token = Message.create(
            {"body": Markup("<p>%s</p>") % ("x" * 400), "message_type": "comment"}
        )
        self.assertNotEqual(long_token.preview, "[...]")
        self.assertEqual(len(long_token.preview), 190)
        self.assertTrue(long_token.preview.startswith("xxxx"))
        self.assertTrue(long_token.preview.endswith("[...]"))

        prose = Message.create(
            {"body": Markup("<p>%s</p>") % ("word " * 100), "message_type": "comment"}
        )
        self.assertTrue(prose.preview.startswith("word word"))
        self.assertEqual(len(prose.preview), 190)

        short = Message.create({"body": "<p>short</p>", "message_type": "comment"})
        self.assertEqual(short.preview, "short", "a body under budget is untouched")

    @users("employee")
    def test_attachment_access_is_decided_per_record(self):
        attachment = (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": "on-document",
                    "raw": b"x",
                    "res_model": "mail.test.simple",
                    "res_id": self.record.id,
                }
            )
        )
        self.env.flush_all()
        checked = []
        attachment_model = type(self.env["ir.attachment"])
        original_check = attachment_model.check_access

        def spy(records, operation):
            if (
                records._name == "ir.attachment"
                and operation == "read"
                and attachment.id in records.ids
            ):
                checked.append(set(records.ids))
            return original_check(records, operation)

        values = {
            "body": "<p>b</p>",
            "message_type": "comment",
            "model": "mail.test.simple",
            "res_id": self.record.id,
            "attachment_ids": [(4, attachment.id)],
        }
        self.patch(attachment_model, "check_access", spy)
        self.env["mail.message"].create([dict(values)])
        alone = len(checked)
        checked.clear()
        self.env["mail.message"].create(
            [
                dict(values),
                {
                    "body": "<p>b</p>",
                    "message_type": "comment",
                    "attachment_ids": [(0, 0, {"name": "new", "raw": b"y"})],
                },
            ]
        )
        batched = len(checked)

        self.assertEqual(
            alone,
            batched,
            "an unrelated sibling using (0, 0, {...}) must not withdraw the "
            "document-scoped exemption from this record: "
            f"{alone} check(s) alone, {batched} batched",
        )

    @users("employee")
    def test_reaction_toggle_reads_the_group_once(self):
        message = self._post()
        self.env.flush_all()
        self.env.invalidate_all()
        selects = []
        cursor_class = type(self.env.cr)
        original_execute = cursor_class.execute

        def spy(cr, query, params=None, log_exceptions=True):
            text = str(query)
            if "mail_message_reaction" in text and "SELECT" in text:
                selects.append(text)
            if params is None:
                return original_execute(cr, query)
            return original_execute(cr, query, params, log_exceptions)

        self.patch(cursor_class, "execute", spy)
        message._message_reaction(
            "\U0001f44d",
            "add",
            self.env.user.partner_id,
            self.env["mail.guest"],
            Store(),
        )
        self.assertEqual(
            len(selects), 1, f"one toggle must read the group once, got {len(selects)}"
        )
        self.assertEqual(len(message.sudo().reaction_ids), 1)

    @users("employee")
    def test_reaction_refuses_an_empty_or_oversized_content(self):
        message = self._post()
        self.env.flush_all()
        broadcasts = []
        self.patch(
            type(message),
            "_bus_send_reaction_group",
            lambda m, content, group=None: broadcasts.append(content),
        )
        for content in ("", "   ", "\U0001f44d" * 33):
            with self.subTest(content=content), self.assertRaises(ValueError):
                message._message_reaction(
                    content,
                    "add",
                    self.env.user.partner_id,
                    self.env["mail.guest"],
                    Store(),
                )
        self.assertFalse(broadcasts)
        self.assertFalse(message.sudo().reaction_ids)

    def test_needaction_search_needs_no_notification_acl(self):
        public_user = self.env.ref("base.public_user")
        self.assertFalse(
            self.env["mail.message"]
            .with_user(public_user)
            .search([("needaction", "=", True)])
        )

    @users("employee")
    def test_unlink_scans_access_once(self):
        message = self.record.with_env(self.env).message_post(
            body="<p>b</p>", message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        self.assertFalse(message.env.su)
        self.env.flush_all()
        self.env.invalidate_all()
        operations = []
        original = type(message)._get_forbidden_access

        def spy(records, operation):
            operations.append(operation)
            return original(records, operation)

        self.patch(type(message), "_get_forbidden_access", spy)
        message.unlink()
        self.assertEqual(operations.count("unlink"), 1)
        self.assertFalse(message.exists())

    @users("employee")
    def test_store_adds_each_thread_once_not_once_per_message(self):
        messages = self.env["mail.message"]
        for index in range(10):
            messages |= self._post(body=f"<p>m{index}</p>")
        self.env.flush_all()
        self.env.invalidate_all()
        thread_adds = []
        original_add = Store.add

        def spy(store, records, *args, **kwargs):
            if getattr(records, "_name", None) == "mail.test.simple":
                thread_adds.append(records.id)
            return original_add(store, records, *args, **kwargs)

        self.patch(Store, "add", spy)
        Store().add(messages).get_result()
        self.assertLessEqual(
            len(thread_adds),
            len(messages) + 1,
            "the thread-fields loop must iterate distinct records, so only the "
            f"per-message reference remains: {len(thread_adds)} adds for "
            f"{len(messages)} messages",
        )

    @users("employee")
    def test_msg_vals_is_rejected_for_several_messages(self):
        first = self._post()
        second = self._post()
        self.env.flush_all()
        store = Store()
        with self.assertRaises(ValueError):
            (first + second)._to_store(
                store, ["message_format"], msg_vals={"scheduled_date": False}
            )

    @users("employee")
    def test_boolean_search_methods_answer_both_polarities(self):
        partner = self.env.user.partner_id
        needing, read, never = (self._post(body=f"<p>{name}</p>") for name in "abc")
        self.env["mail.notification"].sudo().create(
            [
                {
                    "mail_message_id": needing.id,
                    "res_partner_id": partner.id,
                    "notification_type": "inbox",
                    "notification_status": "sent",
                    "is_read": False,
                },
                {
                    "mail_message_id": read.id,
                    "res_partner_id": partner.id,
                    "notification_type": "inbox",
                    "notification_status": "sent",
                    "is_read": True,
                },
            ]
        )
        needing.sudo().starred_partner_ids = [(4, partner.id)]
        self.env.flush_all()
        self.env.invalidate_all()

        Message = self.env["mail.message"]
        scope = [("id", "in", (needing + read + never).ids)]
        for field_name, expected in (
            ("needaction", needing),
            ("starred", needing),
        ):
            everything = needing + read + never
            for operator, operand, wanted in (
                ("=", True, expected),
                ("=", False, everything - expected),
                ("!=", True, everything - expected),
                ("in", [True], expected),
                ("in", [False], everything - expected),
                ("not in", [True], everything - expected),
                ("in", [True, False], everything),
                ("not in", [True, False], Message),
            ):
                with self.subTest(field=field_name, operator=operator, operand=operand):
                    self.assertEqual(
                        Message.search(scope + [(field_name, operator, operand)]),
                        wanted,
                    )
