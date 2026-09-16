import json
from io import BytesIO
from unittest.mock import patch

from odoo import Command, http
from odoo.db.cursor import Cursor
from odoo.tests.common import HttpCase, RecordCapturer, tagged
from odoo.tools import mute_logger

from .test_document_common import TEXT, TransactionCaseDocuments
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.document.controllers.document import ShareRoute
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestDocumentsPdfSplitTargets(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.splitter = mail_new_test_user(
            cls.env,
            login="round5_splitter",
            password="round5_splitter",
            groups="base.group_user,document.group_documents_user",
        )

    def _split(self, document_id):
        return self.url_open(
            "/documents/pdf_split",
            data={
                "vals": "{}",
                "new_files": json.dumps(
                    [
                        {
                            "name": "out",
                            "new_pages": [
                                {
                                    "old_file_type": "document",
                                    "old_file_index": document_id,
                                    "old_page_number": 1,
                                }
                            ],
                        }
                    ]
                ),
                "csrf_token": http.Request.csrf_token(self),
            },
        )

    @mute_logger("odoo.http")
    def test_split_a_document_with_no_content(self):
        self.authenticate("round5_splitter", "round5_splitter")
        document = (
            self.env["document.document"]
            .with_user(self.splitter)
            .create({"name": "awaiting.pdf", "type": "binary"})
        )
        self.assertFalse(document.attachment_id)
        self.assertEqual(self._split(document.id).status_code, 400)

    @mute_logger("odoo.http")
    def test_split_a_shortcut(self):
        self.authenticate("round5_splitter", "round5_splitter")
        Document = self.env["document.document"].with_user(self.splitter)
        target = Document.create({"name": "real.pdf", "type": "binary", "datas": TEXT})
        shortcut = target.action_create_shortcut(location_user_folder_id="MY")
        self.assertFalse(shortcut.attachment_id)
        self.assertEqual(self._split(shortcut.id).status_code, 400)

    @mute_logger("odoo.http")
    def test_split_a_document_that_does_not_exist(self):
        self.authenticate("round5_splitter", "round5_splitter")
        missing_id = (
            self.env["document.document"].search([], order="id desc", limit=1).id
        )
        self.assertIn(self._split(missing_id + 10_000).status_code, (400, 403, 404))


@tagged("post_install", "-at_install")
class TestDocumentsUploadRoute(HttpCase, TransactionCaseDocuments):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plain_internal = cls.env["res.users"].create(
            {
                "login": "plain_internal",
                "password": "plain_internal",
                "name": "Plain internal",
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )
        cls.doc_user.password = "doc_user_pwd"

    def _upload(self, **fields):
        return self.url_open(
            "/documents/upload/",
            data={"csrf_token": http.Request.csrf_token(self), **fields},
            files={"ufile": ("hardening.txt", BytesIO(b"payload"), "text/plain")},
        )

    def test_root_upload_cannot_link_to_an_unwritable_record(self):
        self.authenticate("plain_internal", "plain_internal")
        company = self.env.ref("base.main_company")
        self.assertFalse(
            company.with_user(self.plain_internal).has_access("write"),
            "the fixture only means anything while the user cannot write it",
        )
        attachment_domain = [
            ("res_model", "=", "res.company"),
            ("res_id", "=", company.id),
        ]
        before = self.env["ir.attachment"].search_count(attachment_domain)
        with mute_logger("odoo.http"):
            response = self._upload(
                user_folder_id="MY",
                res_model="res.company",
                res_id=str(company.id),
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.env["ir.attachment"].search_count(attachment_domain),
            before,
            "nothing may be filed on a record the uploader cannot write",
        )

    def test_direct_cloud_upload_needs_a_provider(self):
        self.authenticate("plain_internal", "plain_internal")
        self.env["ir.config_parameter"].sudo().set_param("cloud_storage_provider", "")
        before = self.env["document.document"].search_count([])
        with mute_logger("odoo.http"):
            response = self._upload(user_folder_id="MY", cloud_storage="1")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.env["document.document"].search_count([]), before)

    def test_direct_cloud_upload_answers_with_upload_info(self):
        if not self.env["ir.module.module"].search_count(
            [("name", "=", "cloud_storage"), ("state", "=", "installed")]
        ):
            self.skipTest("cloud_storage is not installed")
        self.authenticate("plain_internal", "plain_internal")
        self.env["ir.config_parameter"].sudo().set_param(
            "cloud_storage_provider", "fake"
        )
        Attachment = type(self.env["ir.attachment"])
        upload_info = {"url": "https://cloud.test/upload", "method": "PUT"}
        with (
            patch.object(
                Attachment,
                "_generate_cloud_storage_url",
                lambda att: f"https://cloud.test/{att.id}",
            ),
            patch.object(
                Attachment,
                "_generate_cloud_storage_upload_info",
                lambda att: upload_info,
            ),
            RecordCapturer(self.env["document.document"], []) as capture,
        ):
            response = self._upload(
                user_folder_id="MY", cloud_storage="1", file_size="12345"
            )
            response.raise_for_status()
        document = capture.records.check_singleton()
        self.assertEqual(
            response.json(), {"document_ids": [document.id], "upload_info": upload_info}
        )
        attachment = document.attachment_id
        self.assertEqual(attachment.type, "cloud_storage")
        self.assertEqual(attachment.url, f"https://cloud.test/{attachment.id}")
        self.assertEqual(
            attachment.file_size,
            12345,
            "the announced size replaces the empty upload's",
        )
        self.assertFalse(
            attachment.raw, "the bytes live in the cloud, not in the filestore"
        )

    def test_root_upload_still_works_without_a_linked_record(self):
        self.authenticate("plain_internal", "plain_internal")
        with RecordCapturer(self.env["document.document"], []) as capture:
            response = self._upload(user_folder_id="MY")
            response.raise_for_status()
        document = capture.records.check_singleton()
        self.assertEqual(document.owner_id, self.plain_internal)
        self.assertFalse(document.res_model)

    def test_root_upload_may_link_to_a_writable_record(self):
        self.doc_user.group_ids += self.env.ref("base.group_partner_manager")
        self.authenticate("documents@example.com", "doc_user_pwd")
        partner = self.env["res.partner"].create({"name": "hardening target"})
        self.assertTrue(partner.with_user(self.doc_user).has_access("write"))
        with RecordCapturer(self.env["document.document"], []) as capture:
            response = self._upload(
                user_folder_id="MY",
                res_model="res.partner",
                res_id=str(partner.id),
            )
            response.raise_for_status()
        document = capture.records.check_singleton()
        self.assertEqual(document.res_model, "res.partner")
        self.assertEqual(document.res_id, partner.id)


@tagged("post_install", "-at_install")
class TestDocumentsPdfSplitInput(TransactionCaseDocuments):
    def test_pdf_split_rejects_out_of_range_indices(self):
        with self.assertRaises(ValueError):
            self.env["ir.attachment"]._pdf_split(
                new_files=[
                    {
                        "name": "x",
                        "new_pages": [{"old_file_index": 99, "old_page_number": 1}],
                    }
                ],
                open_files=[],
            )


@tagged("post_install", "-at_install")
class TestDocumentsMultiFileUpload(HttpCase):
    """Dropping several files into a folder in ONE request.

    Nothing covered this path before, and it is the one the Documents kanban
    uses for a drag-and-drop of more than one file. Its documents are now
    created in a single `create()` rather than one per file, so the thing worth
    pinning is that batching keeps each file paired with its own values.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uploader = mail_new_test_user(
            cls.env,
            login="multi_uploader",
            password="multi_uploader",
            groups="base.group_user,document.group_documents_user",
        )
        cls.folder = (
            cls.env["document.document"]
            .with_user(cls.uploader)
            .create({"name": "Drop Zone", "type": "folder"})
        )

    def _upload(self, payloads):
        return self.url_open(
            f"/documents/upload/{self.folder.access_token}",
            data={"csrf_token": http.Request.csrf_token(self)},
            files=[
                ("ufile", (name, BytesIO(body), "text/plain"))
                for name, body in payloads
            ],
        )

    def test_every_file_becomes_its_own_document_with_its_own_content(self):
        self.authenticate("multi_uploader", "multi_uploader")
        payloads = [
            (f"file-{index}.txt", f"body-{index}".encode()) for index in range(5)
        ]

        with RecordCapturer(self.env["document.document"], []) as capture:
            response = self._upload(payloads)
        response.raise_for_status()

        documents = capture.records
        self.assertEqual(len(documents), 5)
        # Pairing is the whole risk of batching: a shifted zip would still
        # create five documents, each holding the wrong file.
        self.assertEqual(
            [(d.name, d.attachment_id.raw) for d in documents.sorted("name")],
            payloads,
        )
        self.assertEqual(
            documents.mapped("folder_id"),
            self.folder,
            "every one lands in the folder that was uploaded to",
        )
        self.assertEqual(set(response.json()), set(documents.ids))

    def test_each_uploaded_document_is_announced_on_its_own_thread(self):
        self.authenticate("multi_uploader", "multi_uploader")

        with RecordCapturer(self.env["document.document"], []) as capture:
            self._upload([("one.txt", b"1"), ("two.txt", b"2")]).raise_for_status()

        for document in capture.records:
            self.assertTrue(
                self.env["mail.message"].search_count(
                    [
                        ("model", "=", "document.document"),
                        ("res_id", "=", document.id),
                        ("body", "like", "Document uploaded by"),
                    ]
                ),
                f"{document.name} got no upload message of its own",
            )

    def test_the_post_hook_receives_each_document_with_its_own_values(self):
        """The contract batching introduced, pinned directly.

        `_documents_upload_post(document, vals)` promises that `vals` is the
        one `document` was created from. Nothing observable through the default
        hook depends on that -- its message is the same for every file -- so a
        misaligned pairing passes every end-to-end assertion while quietly
        handing an override the wrong record. Checked at the hook itself.
        """
        self.authenticate("multi_uploader", "multi_uploader")
        seen = []
        original = ShareRoute._documents_upload_post

        def spy(controller, document_sudo, vals):
            seen.append((document_sudo.attachment_id.id, vals.get("attachment_id")))
            return original(controller, document_sudo, vals)

        with patch.object(ShareRoute, "_documents_upload_post", spy):
            self._upload(
                [(f"pair-{index}.txt", f"body-{index}".encode()) for index in range(4)]
            ).raise_for_status()

        self.assertEqual(len(seen), 4, "the hook runs once per uploaded file")
        for document_attachment, vals_attachment in seen:
            self.assertEqual(
                document_attachment,
                vals_attachment,
                "the hook was handed a document that does not match its values",
            )

    def test_a_single_file_still_works(self):
        """Negative control: the batched path must not need a crowd."""
        self.authenticate("multi_uploader", "multi_uploader")

        with RecordCapturer(self.env["document.document"], []) as capture:
            self._upload([("alone.txt", b"solo")]).raise_for_status()

        document = capture.records.check_singleton()
        self.assertEqual(document.name, "alone.txt")
        self.assertEqual(document.attachment_id.raw, b"solo")


@tagged("post_install", "-at_install")
class TestDocumentsMultiFileUploadCost(HttpCase):
    """Uploading N files must not cost N times uploading one.

    A budget would be the wrong guard here: it only fails ABOVE itself, so it
    passes both when the code improves and, at a loose enough value, when it
    regresses. What is asserted instead is the SHAPE -- the marginal cost of
    one extra file in the same request. Per-file document creation measured
    13.1 queries per extra file through this route; batching the creates
    measured 4.0, the remainder being the attachment insert and its res_model
    write, which are per-file by construction.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uploader = mail_new_test_user(
            cls.env,
            login="cost_uploader",
            password="cost_uploader",
            groups="base.group_user,document.group_documents_user",
        )
        cls.folder = (
            cls.env["document.document"]
            .with_user(cls.uploader)
            .create({"name": "Cost Zone", "type": "folder"})
        )

    def _cost_of_uploading(self, count, tag):
        """Queries the SERVER runs for one upload request, not the test's."""
        calls = {"n": 0}
        original = Cursor.execute

        def spy(cursor, *args, **kwargs):
            calls["n"] += 1
            return original(cursor, *args, **kwargs)

        with patch.object(Cursor, "execute", spy):
            response = self.url_open(
                f"/documents/upload/{self.folder.access_token}",
                data={"csrf_token": http.Request.csrf_token(self)},
                files=[
                    ("ufile", (f"{tag}{index}.txt", BytesIO(b"payload"), "text/plain"))
                    for index in range(count)
                ],
            )
        response.raise_for_status()
        self.assertEqual(len(response.json()), count)
        return calls["n"]

    def test_the_marginal_cost_of_one_more_file_is_small(self):
        self.authenticate("cost_uploader", "cost_uploader")
        self._cost_of_uploading(1, "warm")  # the caches a first request fills

        one = self._cost_of_uploading(1, "one")
        eleven = self._cost_of_uploading(11, "eleven")
        marginal = (eleven - one) / 10

        self.assertLess(
            marginal,
            7,
            f"one extra file in the same request costs {marginal:.1f} queries "
            f"({one} for 1, {eleven} for 11): the documents are being created "
            f"one per file again",
        )
