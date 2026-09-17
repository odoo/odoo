import base64
import json
import zipfile
from io import BytesIO
from urllib.parse import quote

from reportlab.pdfgen import canvas

from odoo import Command, http
from odoo.tests.common import HttpCase, tagged
from odoo.tools import mute_logger
from odoo.tools.pdf import PdfReader

from .test_document_common import GIF, TransactionCaseDocuments
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestDocumentsPublicRouteHardening(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uploader = mail_new_test_user(
            cls.env,
            login="round4_uploader",
            groups="document.group_documents_user",
            name="Round4 Uploader",
        )
        png = base64.b64decode(
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQ"
            b"DwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        cls.shared_image = cls.env["document.document"].create(
            {
                "name": "round4.png",
                "type": "binary",
                "raw": png,
                "mimetype": "image/png",
                "access_via_link": "view",
            }
        )
        cls.shared_image.write(
            {"thumbnail": base64.b64encode(png), "thumbnail_status": "present"}
        )

    def test_public_thumbnail_rejects_negative_dimensions(self):
        token = self.shared_image.access_token
        self.assertEqual(
            self.url_open(f"/documents/thumbnail/{token}").status_code, 200
        )
        sized = self.url_open(f"/documents/thumbnail/{token}?width=64&height=64")
        self.assertEqual(sized.status_code, 200)
        for query in ("width=-1&height=-1", "width=0&height=-5", "width=-5"):
            with self.subTest(query=query):
                self.assertEqual(
                    self.url_open(f"/documents/thumbnail/{token}?{query}").status_code,
                    400,
                )

    @mute_logger("odoo.http")
    def test_pdf_split_rejects_malformed_payloads(self):
        self.authenticate("round4_uploader", "round4_uploader")
        malformed = [
            '[{"name":"x"}]',
            '[{"name":"x","new_pages":5}]',
            '[{"name":"x","new_pages":[{"old_file_index":0}]}]',
            '{"a":1}',
            (
                '[{"name":"x","new_pages":[{"old_file_type":"document",'
                '"old_file_index":"abc","old_page_number":1}]}]'
            ),
            '[{"new_pages":[]}]',
            "not-json",
        ]
        for payload in malformed:
            with self.subTest(payload=payload):
                res = self.url_open(
                    "/documents/pdf_split",
                    data={
                        "new_files": payload,
                        "vals": "{}",
                        "csrf_token": http.Request.csrf_token(self),
                    },
                )
                self.assertEqual(res.status_code, 400, payload)

    @mute_logger("odoo.http")
    def test_pdf_split_refuses_a_source_that_holds_no_pdf(self):
        not_a_pdf = self.env["document.document"].create(
            {
                "name": "notes.txt",
                "type": "binary",
                "raw": b"plain text, definitely not a pdf",
                "owner_id": self.uploader.id,
            }
        )
        pending_request = self.env["document.document"].create(
            {"name": "awaited.pdf", "type": "binary", "owner_id": self.uploader.id}
        )
        self.assertFalse(pending_request.attachment_id)
        self.authenticate("round4_uploader", "round4_uploader")

        for document in (not_a_pdf, pending_request):
            with self.subTest(document=document.name):
                res = self.url_open(
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
                                            "old_file_index": document.id,
                                            "old_page_number": 1,
                                        }
                                    ],
                                }
                            ]
                        ),
                        "csrf_token": http.Request.csrf_token(self),
                    },
                )
                self.assertEqual(res.status_code, 400)

    def test_folder_zip_is_streamed_and_complete(self):
        Document = self.env["document.document"]
        folder = Document.create(
            {"name": "Streamed", "type": "folder", "access_via_link": "view"}
        )
        subfolder = Document.create(
            {
                "name": "Nested",
                "type": "folder",
                "folder_id": folder.id,
                "access_via_link": "view",
            }
        )
        Document.create(
            [
                {
                    "name": f"payload{index}.bin",
                    "type": "binary",
                    "folder_id": parent.id,
                    "access_via_link": "view",
                    "raw": bytes(300_000),
                }
                for index, parent in enumerate((folder, folder, subfolder))
            ]
        )

        response = self.url_open(f"/documents/content/{folder.access_token}")
        response.raise_for_status()

        self.assertEqual(response.headers.get("Transfer-Encoding"), "chunked")
        self.assertNotIn("Content-Length", response.headers)

        archive = zipfile.ZipFile(BytesIO(response.content))
        self.assertIsNone(archive.testzip(), "the archive must not be corrupt")
        names = set(archive.namelist())
        self.assertEqual(
            names,
            {"payload0.bin", "payload1.bin", "Nested/", "Nested/payload2.bin"},
            "every descendant, and the folder entry itself, must be present",
        )
        self.assertEqual(
            {info.file_size for info in archive.infolist() if not info.is_dir()},
            {300_000},
            "content must survive the chunked copy intact",
        )

    def test_zip_skips_content_the_archive_cannot_carry(self):
        Document = self.env["document.document"]
        folder = Document.create(
            {"name": "Mixed", "type": "folder", "access_via_link": "view"}
        )
        Document.create(
            {
                "name": "local.bin",
                "type": "binary",
                "folder_id": folder.id,
                "access_via_link": "view",
                "raw": b"local bytes",
            }
        )
        remote_attachment = self.env["ir.attachment"].create(
            {
                "name": "remote.bin",
                "type": "binary",
                "url": "https://example.invalid/blob/abc",
                "public": True,
            }
        )
        Document.create(
            {
                "name": "remote.bin",
                "type": "binary",
                "folder_id": folder.id,
                "access_via_link": "view",
                "attachment_id": remote_attachment.id,
            }
        )

        response = self.url_open(f"/documents/content/{folder.access_token}")
        response.raise_for_status()

        archive = zipfile.ZipFile(BytesIO(response.content))
        self.assertIsNone(archive.testzip(), "the archive must not be corrupt")
        self.assertEqual(archive.namelist(), ["local.bin"])
        self.assertEqual(archive.read("local.bin"), b"local bytes")

    @mute_logger("odoo.http", "odoo.addons.document.controllers.documents")
    def test_oversized_zip_is_refused_before_streaming_starts(self):
        Document = self.env["document.document"]
        folder = Document.create(
            {"name": "Too big", "type": "folder", "access_via_link": "view"}
        )
        Document.create(
            [
                {
                    "name": f"file{index}.bin",
                    "type": "binary",
                    "folder_id": folder.id,
                    "access_via_link": "view",
                    "raw": bytes(1000),
                }
                for index in range(3)
            ]
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "document.zip_max_file_count", "1"
        )

        response = self.url_open(f"/documents/content/{folder.access_token}")

        self.assertEqual(response.status_code, 413)
        self.assertNotEqual(
            response.content[:2], b"PK", "no partial archive may be served"
        )

    def test_zip_cap_counts_directories_too(self):
        """A tree of empty folders is work, and the cap has to see it.

        A directory contributes no bytes but one `_get_folder_children` search,
        and the walk is bounded only by the number of folders. Counting files
        alone left an unauthenticated folder-share link able to ask a worker for
        one search per folder, at any depth, which is precisely what the cap
        exists to stop.
        """
        Document = self.env["document.document"]
        folder = Document.create(
            {"name": "Deep", "type": "folder", "access_via_link": "view"}
        )
        Document.create(
            [
                {
                    "name": f"sub{index}",
                    "type": "folder",
                    "folder_id": folder.id,
                    "access_via_link": "view",
                }
                for index in range(3)
            ]
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "document.zip_max_file_count", "1"
        )

        response = self.url_open(f"/documents/content/{folder.access_token}")

        self.assertEqual(
            response.status_code, 413, "subfolders alone did not reach the cap"
        )
        self.assertNotEqual(
            response.content[:2], b"PK", "no partial archive may be served"
        )

    def test_zip_cap_counts_entry_names_too(self):
        Document = self.env["document.document"]
        root = Document.create(
            {"name": "Deep", "type": "folder", "access_via_link": "view"}
        )
        parent = root
        for index in range(25):
            parent = Document.create(
                {
                    "name": f"level-with-a-long-enough-name-{index}",
                    "type": "folder",
                    "folder_id": parent.id,
                    "access_via_link": "view",
                }
            )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("document.zip_max_file_count", "10000")
        ICP.set_param("document.zip_max_total_size", "1000")

        response = self.url_open(f"/documents/content/{root.access_token}")

        self.assertEqual(
            response.status_code,
            413,
            "the names alone are far past a 1000-byte cap, whatever the content weighs",
        )
        self.assertNotEqual(
            response.content[:2], b"PK", "no partial archive may be served"
        )

    def test_a_tree_within_the_byte_cap_is_still_served(self):
        Document = self.env["document.document"]
        root = Document.create(
            {"name": "Shallow", "type": "folder", "access_via_link": "view"}
        )
        Document.create(
            {
                "name": "a.txt",
                "type": "binary",
                "folder_id": root.id,
                "access_via_link": "view",
                "raw": b"hello",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("document.zip_max_total_size", "100000")

        response = self.url_open(f"/documents/content/{root.access_token}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content[:2], b"PK")

    def _make_pdf_document(self, pages=3):
        stream = BytesIO()
        pdf = canvas.Canvas(stream)
        for page in range(pages):
            pdf.drawString(100, 100, f"page {page}")
            pdf.showPage()
        pdf.save()
        return self.env["document.document"].create(
            {
                "name": "source.pdf",
                "type": "binary",
                "raw": stream.getvalue(),
                "mimetype": "application/pdf",
                "owner_id": self.uploader.id,
            }
        )

    def test_pdf_split_accepts_numeric_strings(self):
        source = self._make_pdf_document(pages=2)
        self.authenticate("round4_uploader", "round4_uploader")
        res = self.url_open(
            "/documents/pdf_split",
            data={
                "vals": json.dumps({"owner_id": self.uploader.id}),
                "new_files": json.dumps(
                    [
                        {
                            "name": "stringy",
                            "new_pages": [
                                {
                                    "old_file_type": "document",
                                    "old_file_index": str(source.id),
                                    "old_page_number": "2",
                                }
                            ],
                        }
                    ]
                ),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        res.raise_for_status()
        self.assertEqual(len(self.env["document.document"].browse(res.json())), 1)

    def test_pdf_split_still_splits(self):
        stream = BytesIO()
        pdf = canvas.Canvas(stream)
        for page in range(3):
            pdf.drawString(100, 100, f"page {page}")
            pdf.showPage()
        pdf.save()
        source = self.env["document.document"].create(
            {
                "name": "source.pdf",
                "type": "binary",
                "raw": stream.getvalue(),
                "mimetype": "application/pdf",
                "owner_id": self.uploader.id,
            }
        )
        self.authenticate("round4_uploader", "round4_uploader")

        res = self.url_open(
            "/documents/pdf_split",
            data={
                "vals": json.dumps({"owner_id": self.uploader.id}),
                "new_files": json.dumps(
                    [
                        {
                            "name": "first two",
                            "new_pages": [
                                {
                                    "old_file_type": "document",
                                    "old_file_index": source.id,
                                    "old_page_number": 1,
                                },
                                {
                                    "old_file_type": "document",
                                    "old_file_index": source.id,
                                    "old_page_number": 2,
                                },
                            ],
                        },
                        {
                            "name": "last one",
                            "new_pages": [
                                {
                                    "old_file_type": "document",
                                    "old_file_index": source.id,
                                    "old_page_number": 3,
                                }
                            ],
                        },
                    ]
                ),
                "archive": "true",
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        res.raise_for_status()

        documents = self.env["document.document"].browse(res.json())
        self.assertEqual(len(documents), 2)
        self.assertEqual(documents.mapped("name"), ["first two.pdf", "last one.pdf"])
        page_counts = [
            len(PdfReader(BytesIO(document.raw), strict=False).pages)
            for document in documents
        ]
        self.assertEqual(page_counts, [2, 1], "pages must be routed to the right file")
        self.assertFalse(
            source.active, "archive=true must still send the original to the trash"
        )

    def test_company_root_upload_grants_the_uploader_edit(self):
        self.authenticate("round4_uploader", "round4_uploader")
        res = self.url_open(
            "/documents/upload/",
            data={
                "user_folder_id": "COMPANY",
                "csrf_token": http.Request.csrf_token(self),
            },
            files=[
                ("ufile", ("a.txt", BytesIO(b"a"), "text/plain")),
                ("ufile", ("b.txt", BytesIO(b"b"), "text/plain")),
                ("ufile", ("c.txt", BytesIO(b"c"), "text/plain")),
            ],
        )
        res.raise_for_status()
        documents = self.env["document.document"].browse(res.json())
        self.assertEqual(len(documents), 3)
        for document in documents:
            with self.subTest(document=document.name):
                self.assertFalse(document.folder_id)
                self.assertFalse(document.owner_id)
                self.assertEqual(
                    document.with_user(self.uploader).user_permission,
                    "edit",
                    "the uploader must be able to manage the file they uploaded",
                )
        self.assertFalse(
            self.env["document.access.tracking"]
            .search([], order="id desc", limit=1)
            .filtered(lambda tracking: set(tracking.documents) & set(documents.ids)),
            "granting at create time must not queue an access-tracking entry",
        )


@tagged("post_install", "-at_install")
class TestPublicFolderBatch(HttpCase, TransactionCaseDocuments):
    def test_nested_public_folder_renders_subfolder_counts(self):
        root = self.env["document.document"].create(
            {
                "type": "folder",
                "name": "shared root",
                "access_via_link": "view",
                "owner_id": self.doc_user.id,
            }
        )
        sub1, sub2 = self.env["document.document"].create(
            [
                {
                    "type": "folder",
                    "name": f"sub {n}",
                    "folder_id": root.id,
                    "access_via_link": "view",
                    "owner_id": self.doc_user.id,
                }
                for n in (1, 2)
            ]
        )
        self.env["document.document"].create(
            [
                {
                    "type": "binary",
                    "name": "s1-a",
                    "datas": GIF,
                    "folder_id": sub1.id,
                    "access_via_link": "view",
                    "owner_id": self.doc_user.id,
                }
            ]
            + [
                {
                    "type": "binary",
                    "name": f"s2-{i}",
                    "datas": GIF,
                    "folder_id": sub2.id,
                    "access_via_link": "view",
                    "owner_id": self.doc_user.id,
                }
                for i in range(2)
            ]
        )
        res = self.url_open(root.access_url)
        res.raise_for_status()
        body = res.text
        self.assertIn("sub 1", body)
        self.assertIn("sub 2", body)
        self.assertIn("1 documents", body)
        self.assertIn("2 documents", body)


@tagged("post_install", "-at_install")
class TestDocumentsPublicRouteInput(HttpCase, TransactionCaseDocuments):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = [
            cls.env.ref("base.group_user").id,
            cls.env.ref("document.group_documents_user").id,
        ]
        cls.manager = cls.env["res.users"].create(
            {
                "name": "audit_mgr",
                "login": "audit_mgr",
                "password": "audit_mgr",
                "email": "audit_mgr@t.test",
                "group_ids": [
                    Command.set(
                        groups + [cls.env.ref("document.group_documents_manager").id]
                    )
                ],
            }
        )
        cls.uploader = cls.env["res.users"].create(
            {
                "name": "audit_up",
                "login": "audit_up",
                "password": "audit_up",
                "email": "audit_up@t.test",
                "group_ids": [Command.set(groups)],
            }
        )
        cls.victim = cls.env["res.users"].create(
            {
                "name": "audit_vic",
                "login": "audit_vic",
                "password": "audit_vic",
                "email": "audit_vic@t.test",
                "group_ids": [Command.set(groups)],
            }
        )
        cls.viewer = cls.env["res.users"].create(
            {
                "name": "audit_view",
                "login": "audit_view",
                "password": "audit_view",
                "email": "audit_view@t.test",
                "group_ids": [Command.set(groups)],
            }
        )
        Doc = cls.env["document.document"]
        cls.folder = Doc.with_user(cls.manager).create(
            {"type": "folder", "name": "audit_folder", "user_folder_id": "COMPANY"}
        )
        cls.folder.action_update_access_rights(
            access_via_link="edit", partners={cls.uploader.partner_id: ("edit", False)}
        )
        cls.webp = Doc.with_user(cls.manager).create(
            {
                "type": "binary",
                "name": "audit.webp",
                "user_folder_id": "COMPANY",
                "datas": base64.b64encode(b"RIFF....WEBPVP8 "),
                "mimetype": "image/webp",
            }
        )
        cls.webp.action_update_access_rights(
            partners={cls.viewer.partner_id: ("view", False)}
        )

    def test_c3_bad_member_id_is_bad_request(self):
        res = self.url_open(
            f"/documents/{self.folder.access_token}?member_id=NOTANUMBER",
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 400)

    def test_non_ascii_signup_token_is_not_a_server_error(self):
        """A non-ASCII `member_signup_token` must be rejected, not raise.

        `consteq` is `hmac.compare_digest`, which raises TypeError on a `str`
        holding non-ASCII, and the parameter is public and attacker-controlled.
        The route reaches the comparison without a valid document token -- any
        path segment does, since `_from_access_token` simply answers "no
        document" for a bad one -- so the only thing needed is a
        `document.access` id, a small guessable integer.
        """
        invitee = self.env["res.partner"].create(
            {"name": "audit_invitee", "email": "audit_invitee@t.test"}
        )
        private = self.env["document.document"].create(
            {
                "type": "binary",
                "name": "audit_private.txt",
                "folder_id": self.folder.id,
                "access_via_link": "none",
                "access_internal": "none",
            }
        )
        self.patch(
            type(self.env["res.users"]), "_get_signup_invitation_scope", lambda _: "b2c"
        )
        member = self.env["document.access"].create(
            {"document_id": private.id, "partner_id": invitee.id, "role": "view"}
        )
        self.assertTrue(
            member._is_signup_available(),
            "the invitation has to be live, or the token is never compared",
        )
        self.env.flush_all()

        for token, label in (
            ("caf\u00e9-\u00fcn\u00efcode", "non-ascii"),
            ("wrongtoken", "ascii"),
        ):
            with self.subTest(token=label):
                res = self.url_open(
                    f"/documents/not-a-real-token?member_id={member.id}"
                    f"&member_signup_token={quote(token)}",
                    allow_redirects=False,
                )
                self.assertNotEqual(
                    res.status_code, 500, "a bad token is not a server error"
                )
                self.assertEqual(res.status_code, 404)

    def test_c4_pdf_first_page_rejects_non_pdf(self):
        res = self.url_open(
            f"/documents/content/pdf_first_page/{self.webp.access_token}",
            allow_redirects=False,
        )
        self.assertIn(res.status_code, (400, 404))

    def test_bare_odoo_documents_path_is_the_app_not_a_share_link(self):
        # `/odoo/documents` alone used to read the literal `documents` as an
        # access token, sending a portal user to `/documents/documents`.
        self.portal_user.password = "portal_pw"
        self.authenticate("portal_user", "portal_pw")
        res = self.url_open("/odoo/documents", allow_redirects=False)
        self.assertNotIn("/documents/documents", res.headers.get("Location", ""))
        self.assertNotEqual(res.status_code, 404)
        self.authenticate(self.manager.login, self.manager.login)
        res = self.url_open("/odoo/documents", allow_redirects=False)
        self.assertNotIn("/documents/documents", res.headers.get("Location", ""))
        self.assertNotEqual(res.status_code, 404)
