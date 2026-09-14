import base64
import json
import zipfile
from base64 import b64decode, b64encode
from datetime import timedelta
from http import HTTPStatus
from io import BytesIO
from unittest.mock import patch
from urllib.parse import urlencode

from freezegun import freeze_time
from PIL import Image
from reportlab.pdfgen import canvas
from urllib3.util import parse_url

from odoo import Command, fields, http
from odoo.tests.common import RecordCapturer, tagged
from odoo.tools import file_open, mute_logger
from odoo.tools.image import image_process

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.document.controllers.document import ShareRoute
from odoo.addons.document.tests.test_document_common import TEXT
from odoo.addons.mail.tests.common import MockEmail, mail_new_test_user


@tagged("post_install", "-at_install")
class TestDocumentsControllers(HttpCaseWithUserDemo, MockEmail):
    def _assertPathEqual(self, first, second):
        self.assertEqual(parse_url(first).path, parse_url(second).path)

    def _assertPathIn(self, member, container):
        self.assertIn(
            parse_url(member).path,
            {parse_url(expected_url).path for expected_url in container},
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = mail_new_test_user(
            cls.env,
            login="portal_test",
            groups="base.group_portal",
            company_id=cls.env.ref("base.main_company").id,
            name="portal",
            notification_type="email",
        )

        cls.user_manager = mail_new_test_user(
            cls.env,
            login="manager_test",
            groups="document.group_documents_manager",
            company_id=cls.env.ref("base.main_company").id,
            name="manager",
            notification_type="email",
        )

        with file_open("base/static/img/partner_root-image.png", "rb") as file:
            cls.admin_avatar = file.read()
            cls.admin_avatar_b64 = b64encode(cls.admin_avatar)
            cls.user_admin.image_1920 = cls.admin_avatar_b64

        with file_open("document/static/description/icon.png", "rb") as file:
            cls.doc_icon = file.read()
            cls.doc_icon_b64 = b64encode(cls.doc_icon)

        Doc = cls.env["document.document"]

        cls.test_activity_type = cls.env["mail.activity.type"].create(
            {"name": "Test Activity Type"}
        )

        cls.internal_folder = Doc.create(
            {
                "type": "folder",
                "name": "internal folder",
                "access_internal": "edit",
                "access_via_link": "none",
                "owner_id": cls.user_admin.id,
                "create_activity_option": False,
                "create_activity_type_id": cls.test_activity_type.id,
                "create_activity_summary": "test summary",
                "create_activity_note": "test note",
                "create_activity_user_id": cls.user_admin.id,
                "create_activity_date_deadline_range_type": "day",
                "create_activity_date_deadline_range": 5,
            }
        )
        cls.internal_file = Doc.create(
            {
                "type": "binary",
                "name": "internal-file.png",
                "access_internal": "edit",
                "access_via_link": "none",
                "is_access_via_link_hidden": True,
                "owner_id": cls.user_admin.id,
                "folder_id": cls.internal_folder.id,
                "raw": cls.doc_icon,
            }
        )
        cls.internal_file_textual = Doc.create(
            {
                "type": "binary",
                "name": "internal-file-textual.txt",
                "access_internal": "edit",
                "access_via_link": "none",
                "is_access_via_link_hidden": True,
                "owner_id": cls.user_admin.id,
                "folder_id": cls.internal_folder.id,
                "raw": TEXT,
            }
        )
        cls.env["ir.config_parameter"].set_param("ir_attachment.location", "db")
        cls.env["ir.config_parameter"].flush_model()
        cls.internal_file_textual_on_db = Doc.create(
            {
                "type": "binary",
                "name": "internal-file-textual-on-db.txt",
                "access_internal": "edit",
                "access_via_link": "none",
                "is_access_via_link_hidden": True,
                "owner_id": cls.user_admin.id,
                "folder_id": cls.internal_folder.id,
                "raw": TEXT,
            }
        )
        cls.env["ir.config_parameter"].set_param("ir_attachment.location", False)
        cls.env["ir.config_parameter"].flush_model()
        cls.internal_hidden = Doc.create(
            {
                "type": "binary",
                "name": "internal-hidden.png",
                "access_internal": "none",
                "access_via_link": "none",
                "owner_id": cls.user_admin.id,
                "folder_id": cls.internal_folder.id,
                "raw": cls.doc_icon,
            }
        )
        cls.internal_request = Doc.create(
            {
                "type": "binary",
                "name": "internal-request.png",
                "access_internal": "edit",
                "access_via_link": "none",
                "owner_id": cls.user_admin.id,
                "folder_id": cls.internal_folder.id,
            }
        )
        cls.internal_url = Doc.create(
            {
                "type": "url",
                "name": "internal url",
                "access_internal": "edit",
                "access_via_link": "none",
                "owner_id": cls.user_admin.id,
                "folder_id": cls.internal_folder.id,
                "url": f"{cls.base_url()}/web/health",
            }
        )

        cls.public_folder = Doc.create(
            {
                "type": "folder",
                "name": "public folder",
                "access_internal": "edit",
                "access_via_link": "edit",
                "folder_id": cls.internal_folder.id,
                "owner_id": cls.user_admin.id,
            }
        )
        cls.public_file = Doc.create(
            {
                "type": "binary",
                "name": "public-file.png",
                "access_internal": "edit",
                "access_via_link": "view",
                "owner_id": cls.user_admin.id,
                "folder_id": cls.public_folder.id,
                "raw": cls.doc_icon,
            }
        )
        cls.public_file_textual = Doc.create(
            {
                "type": "binary",
                "name": "public-file-textual.txt",
                "access_internal": "edit",
                "access_via_link": "view",
                "owner_id": cls.user_admin.id,
                "folder_id": cls.public_folder.id,
                "raw": TEXT,
            }
        )
        cls.public_request = Doc.create(
            {
                "type": "binary",
                "name": "public-request.png",
                "access_internal": "edit",
                "access_via_link": "edit",
                "owner_id": cls.user_admin.id,
                "folder_id": cls.public_folder.id,
            }
        )
        cls.public_url = Doc.create(
            {
                "type": "url",
                "name": "public url",
                "access_internal": "edit",
                "access_via_link": "view",
                "owner_id": cls.user_admin.id,
                "folder_id": cls.public_folder.id,
                "url": f"{cls.base_url()}/web/health",
            }
        )
        cls.internal_shortcut = cls.internal_file.action_create_shortcut(
            str(cls.public_folder.id)
        )
        cls.missing_file = Doc.new()

        now = fields.Datetime.now()
        cls.env["document.access"].create(
            [
                {
                    "document_id": doc.id,
                    "partner_id": partner.id,
                    "last_access_date": now,
                }
                for doc in [
                    cls.internal_folder,
                    cls.internal_file,
                    cls.internal_shortcut,
                    cls.internal_hidden,
                    cls.internal_request,
                    cls.internal_url,
                    cls.public_folder,
                    cls.internal_file_textual,
                    cls.internal_file_textual_on_db,
                    cls.public_file,
                    cls.public_request,
                    cls.public_url,
                    cls.public_file_textual,
                ]
                for partner in [
                    cls.user_demo.partner_id,
                    cls.user_portal.partner_id,
                ]
            ]
        )

    def test_doc_ctrl_avatar(self):
        avatar_128 = b64decode(self.user_admin.avatar_128)
        placeholder = image_process(
            self.user_admin.partner_id._get_avatar_placeholder(),
            size=(128, 128),
        )

        for document, user, status, content, filename in [
            (self.missing_file, None, 200, placeholder, "avatar_grey.png"),
            (self.public_file, None, 200, avatar_128, '"Mitchell Admin.png"'),
            (self.internal_file, None, 200, placeholder, "avatar_grey.png"),
            (self.internal_shortcut, None, 200, placeholder, "avatar_grey.png"),
            (self.internal_shortcut, "demo", 200, avatar_128, '"Mitchell Admin.png"'),
            (self.internal_file, "demo", 200, avatar_128, '"Mitchell Admin.png"'),
        ]:
            url = f"/documents/avatar/{document.access_token}"
            session = self.authenticate(user, user)
            with self.subTest(document=document.name, user=user):
                res = self.url_open(url)
                self.assertEqual(res.status_code, status)
                if status == 200:
                    self.assertEqual(
                        res.headers.get("Content-Disposition"),
                        f"inline; filename={filename}",
                    )
                    self.assertEqual(res.content, content)
                    self.assertIn("Last-Modified", res.headers)
                    self.assertIn("ETag", res.headers)

        assert session.uid == self.user_demo.id
        assert document is self.internal_file
        res = self.url_open(
            url,
            headers={
                "If-Modified-Since": res.headers["Last-Modified"],
                "If-None-Match": res.headers["ETag"],
            },
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, HTTPStatus.NOT_MODIFIED)

    def test_doc_ctrl_avatar_portal(self):
        placeholder = image_process(
            self.user_admin.partner_id._get_avatar_placeholder(),
            size=(128, 128),
        )
        self.authenticate("portal_test", "portal_test")
        access_portal = self.internal_file.access_ids.filtered(
            lambda access: access.partner_id == self.user_portal.partner_id
        ).check_singleton()
        access_portal.role = "view"

        access_portal.expiration_date = fields.Datetime.now() + timedelta(hours=1)
        res = self.url_open(f"/documents/avatar/{self.internal_file.access_token}")
        res.raise_for_status()
        self.assertEqual(res.content, b64decode(self.user_admin.avatar_128))

        access_portal.expiration_date = fields.Datetime.now() - timedelta(hours=1)
        res = self.url_open(f"/documents/avatar/{self.internal_file.access_token}")
        res.raise_for_status()
        self.assertEqual(res.content, placeholder)

    def test_doc_ctrl_avatar_shortcut(self):
        self.internal_file.action_update_access_rights(
            access_via_link="view",
            is_access_via_link_hidden=False,
        )
        for user in [None, "demo"]:
            with self.subTest(user=user):
                res = self.url_open(
                    f"/documents/avatar/{self.internal_shortcut.access_token}"
                )
                res.raise_for_status()
                self.assertEqual(res.content, b64decode(self.user_admin.avatar_128))

    def test_doc_ctrl_content_binary(self):
        for document, user, dl, status, content in [
            (self.missing_file, None, "1", 404, "not found"),
            (self.internal_file, None, "1", 404, "not found"),
            (
                self.internal_shortcut,
                None,
                "1",
                404,
                "not found",
            ),
            (self.public_file, None, "1", 200, self.doc_icon),
            (self.public_file, None, "0", 200, self.doc_icon),
            (self.public_file, None, "bad", 400, "Use 0/1"),
            (self.public_request, None, "1", 404, "not found"),
            (
                self.internal_file,
                "demo",
                "1",
                200,
                self.doc_icon,
            ),
            (
                self.internal_hidden,
                "demo",
                "1",
                404,
                "not found",
            ),
            (
                self.internal_file,
                "demo",
                "0",
                200,
                self.doc_icon,
            ),
        ]:
            session = self.authenticate(user, user)
            url = f"/documents/content/{document.access_token}?download={dl}"
            with self.subTest(user=user, url=url):
                res = self.url_open(url)
                self.assertEqual(res.status_code, status)
                if status == 200:
                    self.assertEqual(res.content, content)
                    self.assertIn("Last-Modified", res.headers)
                    self.assertIn("ETag", res.headers)
                    self.assertEqual(
                        res.headers.get("Content-Disposition"),
                        ("attachment" if dl == "1" else "inline")
                        + f"; filename={document.name}",
                    )
                else:
                    self.assertIn(content, res.text)

        assert session.uid == self.user_demo.id
        assert url == f"/documents/content/{self.internal_file.access_token}?download=0"
        res = self.url_open(
            url,
            headers={
                "If-Modified-Since": res.headers["Last-Modified"],
                "If-None-Match": res.headers["ETag"],
            },
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, HTTPStatus.NOT_MODIFIED)

    def test_doc_ctrl_content_binary_portal(self):
        self.authenticate("portal_test", "portal_test")
        access_portal = self.internal_file.access_ids.filtered(
            lambda access: access.partner_id == self.user_portal.partner_id
        ).check_singleton()
        access_portal.role = "view"

        access_portal.expiration_date = fields.Datetime.now() + timedelta(hours=1)
        res = self.url_open(f"/documents/content/{self.internal_file.access_token}")
        res.raise_for_status()
        self.assertEqual(res.content, self.doc_icon)

        access_portal.expiration_date = fields.Datetime.now() - timedelta(hours=1)
        res = self.url_open(f"/documents/content/{self.internal_file.access_token}")
        self.assertEqual(res.status_code, 404)

    def test_doc_ctrl_content_binary_shortcut(self):
        self.authenticate("demo", "demo")
        res = self.url_open(f"/documents/content/{self.internal_shortcut.access_token}")
        res.raise_for_status()
        self.assertEqual(res.content, self.doc_icon)

        self.internal_file.action_update_access_rights(
            access_via_link="view",
            is_access_via_link_hidden=False,
        )
        self.authenticate(None, None)
        res = self.url_open(f"/documents/content/{self.internal_shortcut.access_token}")
        res.raise_for_status()
        self.assertEqual(res.content, self.doc_icon)

    def test_doc_ctrl_content_folder(self):
        self.authenticate(None, None)
        res = self.url_open(f"/documents/content/{self.internal_folder.access_token}")
        self.assertEqual(res.status_code, 404)
        res = self.url_open(f"/documents/content/{self.public_folder.access_token}")
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        with zipfile.ZipFile(BytesIO(res.content)) as reszip:
            self.assertEqual(
                reszip.namelist(), ["public-file.png", "public-file-textual.txt"]
            )
            self.assertEqual(reszip.read("public-file.png"), self.doc_icon)

        self.internal_file.action_update_access_rights(
            access_via_link="view",
            is_access_via_link_hidden=False,
        )
        res = self.url_open(f"/documents/content/{self.public_folder.access_token}")
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        with zipfile.ZipFile(BytesIO(res.content)) as reszip:
            self.assertEqual(
                sorted(reszip.namelist()),
                ["internal-file.png", "public-file-textual.txt", "public-file.png"],
            )
            self.assertEqual(reszip.read("internal-file.png"), self.doc_icon)
            self.assertEqual(reszip.read("public-file.png"), self.doc_icon)
            self.assertEqual(reszip.read("public-file-textual.txt"), TEXT)

        self.public_file.action_create_shortcut(str(self.internal_folder.id))
        self.public_folder.action_create_shortcut(str(self.internal_folder.id))
        self.env["document.document"].create(
            [
                {
                    "name": "te/st.tar.gz",
                    "folder_id": self.internal_folder.id,
                    "access_internal": "view",
                    "datas": "test",
                }
                for _ in range(3)
            ]
            + [
                {
                    "name": self.public_folder.name,
                    "datas": "test",
                    "folder_id": self.public_folder.folder_id.id,
                    "access_internal": "view",
                    "type": "folder",
                }
                for _ in range(3)
            ]
            + [
                {
                    "name": ".hidden",
                    "datas": "test",
                    "folder_id": self.public_folder.folder_id.id,
                    "access_internal": "view",
                    "type": "folder",
                }
                for _ in range(2)
            ]
        )

        parent_id = self.public_folder.id
        for i in range(4):
            parent_id = (
                self.env["document.document"]
                .create(
                    {
                        "name": f"folder/test/{i}",
                        "folder_id": parent_id,
                        "type": "folder",
                    }
                )
                .id
            )

        self.authenticate("demo", "demo")
        res = self.url_open(f"/documents/content/{self.internal_folder.access_token}")
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        expected = {
            "internal-file.png",
            "internal-file-textual.txt",
            "internal-file-textual-on-db.txt",
            "public-file.png",
            "public folder/",
            "public folder/public-file.png",
            "public folder/public-file-textual.txt",
            "public folder/internal-file.png",
            "public folder-2/",
            "public folder-3/",
            "public folder-4/",
            "public folder-5/",
            "te_st.tar.gz",
            "te_st-2.tar.gz",
            "te_st-3.tar.gz",
            ".hidden/",
            ".hidden-2/",
            "public folder/folder_test_0/",
            "public folder/folder_test_0/folder_test_1/",
            "public folder/folder_test_0/folder_test_1/folder_test_2/",
            "public folder/folder_test_0/folder_test_1/folder_test_2/folder_test_3/",
        }
        with zipfile.ZipFile(BytesIO(res.content)) as reszip:
            self.assertEqual(set(reszip.namelist()), expected)
            self.assertEqual(reszip.read("internal-file.png"), self.doc_icon)

    def test_doc_ctrl_content_url(self):
        self.authenticate(None, None)
        res = self.url_open(
            f"/documents/content/{self.public_url.access_token}", allow_redirects=False
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, HTTPStatus.TEMPORARY_REDIRECT)
        self.assertEqual(res.headers.get("Location"), self.public_url.url)
        res = self.url_open(
            f"/documents/content/{self.internal_url.access_token}",
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 404)

        self.authenticate("demo", "demo")
        res = self.url_open(
            f"/documents/content/{self.internal_url.access_token}",
            allow_redirects=False,
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, HTTPStatus.TEMPORARY_REDIRECT)
        self.assertEqual(res.headers.get("Location"), self.internal_url.url)

    @mute_logger("odoo.http")
    def test_doc_ctrl_cross_redirection(self):
        docs_url = f"/documents/{self.public_file.access_token}?a=1"
        odoo_url = f"/odoo{docs_url}"
        portal = self.user_portal.login
        demo = self.user_demo.login
        for login, url, code, location in [
            (None, odoo_url, 307, docs_url),
            (portal, odoo_url, 307, docs_url),
            (demo, docs_url, 307, odoo_url),
            (None, docs_url, 200, ...),
            (portal, docs_url, 200, ...),
            (demo, odoo_url, 303, ...),
        ]:
            with self.subTest(login=login, url=url):
                self.authenticate(login, login)
                res = self.url_open(url, allow_redirects=False)
                res.raise_for_status()
                self.assertEqual(res.status_code, code)
                if code == 307:
                    self.assertURLEqual(res.headers.get("Location"), location)

    @mute_logger("odoo.http")
    def test_doc_redirection_partner(self):
        self.patch(
            type(self.env["res.users"]), "_get_signup_invitation_scope", lambda _: "b2c"
        )
        self.public_file.access_via_link = "none"
        access = self.env["document.access"].create(
            {
                "document_id": self.public_file.id,
                "role": "view",
                "partner_id": self.env["res.partner"].create({"name": "Test"}).id,
            }
        )
        member_signup_token = access._get_member_signup_token()
        docs_url = f"/documents/{self.public_file.access_token}?member_signup_token={member_signup_token}&member_id={access.id}"
        res = self.url_open(docs_url, allow_redirects=False)
        res.raise_for_status()
        redirect_url = res.headers.get("Location") or ""
        self.assertIn(
            "/web/signup", redirect_url, f"Invalid redirect URL: {redirect_url}"
        )
        self.assertIn(self.public_file.access_token, redirect_url)

        docs_url = f"/documents/{self.public_file.access_token}?member_signup_token=bad_token_{member_signup_token}&member_id={access.id}"
        res = self.url_open(docs_url, allow_redirects=False)
        self.assertFalse(res.ok)
        redirect_url = res.headers.get("Location") or ""
        self.assertFalse(redirect_url)

        access.last_access_date = fields.Datetime.now()
        access.role = False
        docs_url = f"/documents/{self.public_file.access_token}?member_signup_token={member_signup_token}&member_id={access.id}"
        res = self.url_open(docs_url, allow_redirects=False)
        self.assertFalse(res.ok)

    def test_doc_render_public_templates(self):
        self.authenticate(None, None)

        for doc in (
            self.internal_file,
            self.internal_hidden,
            self.internal_folder,
            self.internal_request,
            self.internal_url,
        ):
            with self.subTest(name=doc.name):
                res = self.url_open(doc.access_url)
                self.assertEqual(res.status_code, 404)
                self.assertIn("does not exist or is not publicly available.", res.text)

        res = self.url_open(self.public_url.access_url, allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, HTTPStatus.TEMPORARY_REDIRECT)

        res = self.url_open(self.public_folder.access_url)
        res.raise_for_status()
        self.assertRegex(res.text, r"0\s+folders,\s+2\s+files")
        self.assertIn(self.public_file.name, res.text)
        self.assertIn(self.public_request.name, res.text)
        self.assertIn(self.public_url.name, res.text)
        self.assertIn(self.public_file_textual.name, res.text)

        self.internal_file.action_update_access_rights(
            access_via_link="view",
            is_access_via_link_hidden=False,
        )
        res = self.url_open(self.public_folder.access_url)
        res.raise_for_status()
        self.assertRegex(res.text, r"0\s+folders,\s+3\s+files")
        self.assertIn(self.public_file.name, res.text)
        self.assertIn(self.public_request.name, res.text)
        self.assertIn(self.public_url.name, res.text)
        self.assertIn(self.internal_file.name, res.text)

        res = self.url_open(self.public_file.access_url)
        res.raise_for_status()
        self.assertIn(self.public_file.name, res.text)
        self.assertIn("Download file", res.text)
        self.assertIn("Preview file", res.text)

        res = self.url_open(self.public_request.access_url)
        res.raise_for_status()
        self.assertIn(
            f"<span>{self.public_request.owner_id.name}</span> is requesting", res.text
        )

    def test_doc_ctrl_thumbnail(self):
        placeholder = self.env["ir.binary"]._get_placeholder_bytes(
            self.internal_file._get_placeholder_filename("thumbnail")
        )

        self.authenticate(None, None)
        res = self.url_open(f"/documents/thumbnail/{self.internal_file.access_token}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, placeholder)
        res = self.url_open(f"/documents/thumbnail/{self.public_file.access_token}")
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        with (
            Image.open(BytesIO(self.doc_icon)) as image,
            Image.open(BytesIO(res.content)) as thumbnail,
        ):
            self.assertEqual(image.size, (100, 100))
            self.assertEqual(thumbnail.size, (100, 70))
        res = self.url_open(
            f"/documents/thumbnail/{self.public_file.access_token}?width=bad"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("bad", res.text)

    def test_doc_ctrl_thumbnail_textual_access(self):
        for document, user, status, content in [
            (self.missing_file, None, 404, "not found"),
            (self.public_request, None, 404, "not found"),
            (self.internal_file, None, 404, "not found"),
            (self.internal_shortcut, None, 404, "not found"),
            (self.internal_hidden, "demo", 404, "not found"),
            (
                self.internal_file_textual,
                None,
                404,
                "not found",
            ),
        ]:
            self.authenticate(user, user)
            res = self.url_open(f"/documents/thumbnail_textual/{document.access_token}")
            self.assertEqual(res.status_code, status)
            self.assertIn(content, res.text)

    def test_doc_ctrl_thumbnail_textual(self):
        TEXT_str = TEXT.decode("utf-8")
        original_file_read = self.registry["ir.attachment"]._read_file
        file_read_patch = patch.object(
            self.registry["ir.attachment"],
            "_read_file",
            side_effect=original_file_read,
            autospec=True,
        )
        for document, user, status, content in [
            (self.public_folder, None, 400, "bad document type"),
            (self.public_url, None, 400, "bad document type"),
            (self.public_file, None, 400, "bad document mimetype"),
            (self.public_file_textual, None, 200, TEXT_str),
            (self.internal_file, "demo", 400, "bad document mimetype"),
            (
                self.internal_file_textual,
                "demo",
                200,
                TEXT_str,
            ),
            (self.internal_file_textual_on_db, "demo", 200, TEXT_str),
        ]:
            self.authenticate(user, user)
            with file_read_patch as patched:
                res = self.url_open(
                    f"/documents/thumbnail_textual/{document.access_token}"
                )
            if document is self.internal_file_textual_on_db:
                patched.assert_not_called()
            elif document is self.internal_file_textual:
                self.assertEqual(
                    patched.call_args.args[1], document.attachment_id.store_fname
                )
                self.assertEqual(patched.call_args.kwargs.get("size"), 4096)
            self.assertEqual(res.status_code, status)
            self.assertIn(content, res.text)

    def test_doc_ctrl_thumbnail_textual_size(self):
        document = self.internal_file.with_user(self.user_manager).copy()
        document.mimetype = "text/plain"
        TESTING_SIZE = 2000
        self.assertGreater(len(document.attachment_id.raw), TESTING_SIZE)

        self.authenticate("demo", "demo")
        with patch.object(ShareRoute, "TEXTUAL_THUMBNAIL_SIZE", 1024):
            res = self.url_open(f"/documents/thumbnail_textual/{document.access_token}")
        self.assertEqual(res.status_code, 200)
        self.assertIn("</pre>", res.text)
        self.assertLess(len(res.content), TESTING_SIZE)

    def test_doc_ctrl_upload_folder_public(self):
        self.authenticate(None, None)

        res = self.url_open(
            f"/documents/upload/{self.internal_folder.access_token}",
            data={
                "csrf_token": http.Request.csrf_token(self),
                "ufile": "",
            },
        )
        self.assertEqual(res.status_code, 404)
        res = self.url_open(
            f"/documents/upload/{self.public_folder.access_token}",
            data={
                "csrf_token": http.Request.csrf_token(self),
                "ufile": "",
            },
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("missing files", res.text)
        res = self.url_open(
            f"/documents/upload/{self.public_folder.access_token}",
            data={
                "csrf_token": http.Request.csrf_token(self),
                "res_model": "res.users",
            },
            files={"ufile": BytesIO()},
        )
        self.assertEqual(res.status_code, HTTPStatus.FORBIDDEN)
        self.assertIn("only internal users can provide field values", res.text)

        with RecordCapturer(self.env["document.document"], []) as capture:
            res = self.url_open(
                f"/documents/upload/{self.public_folder.access_token}",
                data={"csrf_token": http.Request.csrf_token(self)},
                files={"ufile": ("hello.txt", BytesIO(b"Hello"), "text/plain")},
                allow_redirects=False,
            )
            res.raise_for_status()
        document = capture.records.check_singleton()
        self.assertEqual(document.name, "hello.txt")
        self.assertEqual(document.mimetype, "text/plain")
        self.assertEqual(document.access_internal, "edit")
        self.assertEqual(document.access_via_link, "view")
        self.assertEqual(document.folder_id, self.public_folder)
        self.assertEqual(document.owner_id, self.public_folder.owner_id)
        self.assertEqual(document.raw, b"Hello")
        self.assertRegex(document.access_token, r"[A-Za-z0-9-_]{22}")
        self.assertEqual(
            document.message_ids.mapped("body"),
            [
                "<p>Document uploaded by Public user</p>",
                "<p>Document created</p>",
            ],
        )
        self.assertEqual(res.status_code, HTTPStatus.SEE_OTHER)
        self._assertPathEqual(
            res.headers.get("Location"), self.public_folder.access_url
        )
        self.url_open(res.headers["Location"]).raise_for_status()

        with (
            RecordCapturer(self.env["document.document"], []) as record_capture,
            self.assertLogs("odoo.libs.filesystem.mimetypes", "WARNING") as log_capture,
        ):
            res = self.url_open(
                f"/documents/upload/{self.public_folder.access_token}",
                data={"csrf_token": http.Request.csrf_token(self)},
                files={"ufile": ("hello.txt", BytesIO(self.doc_icon), "text/plain")},
                allow_redirects=False,
            )
            res.raise_for_status()
        document = record_capture.records.check_singleton()
        self.assertEqual(
            document.name, "hello.txt.png", "the filename must have been neutralized"
        )
        self.assertEqual(
            document.mimetype, "image/png", "the mimetype must have been neutralized"
        )
        self.assertEqual(document.raw, self.doc_icon)
        self.assertEqual(
            log_capture.output,
            [
                (
                    "WARNING:odoo.libs.filesystem.mimetypes:File 'hello.txt' has an "
                    "invalid extension for mimetype 'image/png', adding '.png'"
                )
            ],
        )
        self.url_open(res.headers["Location"]).raise_for_status()

    def test_doc_ctrl_upload_request_public(self):
        self.authenticate(None, None)

        res = self.url_open(
            f"/documents/upload/{self.public_request.access_token}",
            data={"csrf_token": http.Request.csrf_token(self)},
            files={"ufile": ("hello.txt", BytesIO(b"Hello"), "text/plain")},
            allow_redirects=False,
        )
        res.raise_for_status()
        self.assertEqual(self.public_request.name, "hello.txt")
        self.assertEqual(self.public_request.mimetype, "text/plain")
        self.assertEqual(self.public_request.access_internal, "edit")
        self.assertEqual(self.public_request.access_via_link, "view")
        self.assertEqual(self.public_request.owner_id, self.user_admin)
        self.assertEqual(self.public_request.raw, b"Hello")
        tracking_message_ids = self.public_request.message_ids.filtered(
            "tracking_value_ids"
        )
        self.assertTracking(
            tracking_message_ids,
            [
                ("name", "char", "public-request.png", "hello.txt"),
            ],
            strict=True,
        )
        other_message_ids = self.public_request.message_ids - tracking_message_ids
        self.assertEqual(
            other_message_ids.mapped("body"),
            [
                "<p>Document uploaded by Public user</p>",
                "<p>Document created</p>",
            ],
        )
        self.assertEqual(res.status_code, HTTPStatus.SEE_OTHER)
        self._assertPathEqual(res.headers.get("Location"), "/documents/upload/success")
        self.url_open(res.headers["Location"]).raise_for_status()

        self.public_request.action_update_access_rights(
            access_via_link="edit",
            is_access_via_link_hidden=False,
        )

        shortcut = self.public_request.action_create_shortcut()
        self.assertFalse(shortcut.thumbnail)
        self.assertFalse(self.public_request.thumbnail)

        with self.assertLogs(
            "odoo.libs.filesystem.mimetypes", "WARNING"
        ) as log_capture:
            res = self.url_open(
                f"/documents/upload/{self.public_request.access_token}",
                data={"csrf_token": http.Request.csrf_token(self)},
                files={"ufile": ("hello.txt", BytesIO(self.doc_icon), "text/plain")},
                allow_redirects=False,
            )
            res.raise_for_status()
        self.assertEqual(
            self.public_request.name,
            "hello.txt.png",
            "the filename must have been neutralized",
        )
        self.assertEqual(
            self.public_request.mimetype,
            "image/png",
            "the mimetype must have been neutralized",
        )
        self.assertEqual(self.public_request.raw, self.doc_icon)

        self.assertTrue(shortcut.thumbnail)
        self.assertTrue(self.public_request.thumbnail)

        self.assertEqual(
            log_capture.output,
            [
                (
                    "WARNING:odoo.libs.filesystem.mimetypes:File 'hello.txt' has an "
                    "invalid extension for mimetype 'image/png', adding '.png'"
                )
            ],
        )
        self.url_open(res.headers["Location"]).raise_for_status()

    @freeze_time("2022-07-24 08:00:00")
    def test_doc_upload_folder_user(self):
        self.authenticate("demo", "demo")

        res = self.url_open(
            f"/documents/upload/{self.internal_folder.access_token}",
            data={"csrf_token": http.Request.csrf_token(self), "res_id": "bad"},
            files={"ufile": BytesIO()},
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("bad", res.text)

        self.internal_folder.create_activity_option = True
        with (
            RecordCapturer(self.env["document.document"], []) as capture,
            RecordCapturer(
                self.env["mail.activity"], [("res_model", "=", "document.document")]
            ) as capture_activity,
        ):
            res = self.url_open(
                f"/documents/upload/{self.internal_folder.access_token}",
                data={"csrf_token": http.Request.csrf_token(self)},
                files={"ufile": ("hello.txt", b"Hello", "text/plain")},
                allow_redirects=False,
            )
            res.raise_for_status()

        document = capture.records.check_singleton()
        self.assertEqual(document.name, "hello.txt")
        self.assertEqual(document.mimetype, "text/plain")
        self.assertEqual(document.owner_id, self.user_demo)
        self.assertFalse(document.res_id)
        self.assertFalse(document.res_model)
        self.assertEqual(document.attachment_id.res_id, document.id)
        self.assertEqual(document.attachment_id.res_model, "document.document")
        self.assertEqual(
            document.message_ids.mapped("body"),
            [
                "<p>Document uploaded by Marc Demo</p>",
                "<p>Document created</p>",
            ],
        )
        self.assertFalse(
            capture_activity.records,
            "Activities should only be created when using the mail gateway",
        )

        self.internal_folder.create_activity_option = False
        with (
            RecordCapturer(self.env["document.document"], []) as capture,
            RecordCapturer(
                self.env["mail.activity"], [("res_model", "=", "document.document")]
            ) as capture_activity,
        ):
            res = self.url_open(
                f"/documents/upload/{self.internal_folder.access_token}",
                data={
                    "csrf_token": http.Request.csrf_token(self),
                    "res_id": self.user_demo.partner_id.id,
                    "res_model": "res.partner",
                },
                files={"ufile": ("hello.txt", self.doc_icon, "text/plain")},
            )
            res.raise_for_status()

        self.assertFalse(capture_activity.records)
        document = capture.records.check_singleton()
        self.assertEqual(
            document.name, "hello.txt", "the filename must not have been neutralized"
        )
        self.assertEqual(
            document.mimetype,
            "text/plain",
            "the mimetype must not have been neutralized",
        )
        self.assertEqual(document.res_id, self.user_demo.partner_id.id)
        self.assertEqual(document.res_model, "res.partner")
        self.assertEqual(document.attachment_id.res_id, self.user_demo.partner_id.id)
        self.assertEqual(document.attachment_id.res_model, "res.partner")

    def test_doc_upload_request_user(self):
        self.authenticate("demo", "demo")

        res = self.url_open(
            f"/documents/upload/{self.internal_request.access_token}",
            data={
                "res_id": self.user_demo.id,
                "res_model": "res.users",
                "csrf_token": http.Request.csrf_token(self),
            },
            files={"ufile": ("hello.txt", BytesIO(b"Hello"), "text/plain")},
            allow_redirects=False,
        )
        res.raise_for_status()

        self.assertEqual(self.internal_request.name, "hello.txt")
        self.assertEqual(self.internal_request.mimetype, "text/plain")
        self.assertFalse(self.internal_request.res_id)
        self.assertFalse(self.internal_request.res_model)
        self.assertEqual(
            self.internal_request.attachment_id.res_id, self.internal_request.id
        )
        self.assertEqual(
            self.internal_request.attachment_id.res_model, "document.document"
        )
        self.assertEqual(self.internal_request.raw, b"Hello")
        tracking_message_ids = self.internal_request.message_ids.filtered(
            "tracking_value_ids"
        )
        self.assertTracking(
            tracking_message_ids,
            [
                ("name", "char", "internal-request.png", "hello.txt"),
            ],
            strict=True,
        )
        other_message_ids = self.internal_request.message_ids - tracking_message_ids
        self.assertEqual(
            other_message_ids.mapped("body"),
            [
                "<p>Document uploaded by Marc Demo</p>",
                "<p>Document created</p>",
            ],
        )

        res = self.url_open(
            f"/documents/upload/{self.internal_hidden.access_token}",
            data={"csrf_token": http.Request.csrf_token(self)},
            files={"ufile": ("hello.txt", BytesIO(b"Hello"), "text/plain")},
        )
        self.assertEqual(res.status_code, 404)

        img_byte = BytesIO()
        Image.new(mode="RGB", size=(10_000, 2_000)).save(img_byte, format="PNG")
        img_byte = img_byte.getvalue()

        res = self.url_open(
            f"/documents/upload/{self.internal_request.access_token}",
            data={
                "res_id": self.user_demo.id,
                "res_model": "res.users",
                "csrf_token": http.Request.csrf_token(self),
            },
            files={"ufile": ("test.bmp", img_byte, "image/bmp")},
            allow_redirects=False,
        )
        res.raise_for_status()
        self.assertEqual(self.internal_request.name, "test.bmp")
        self.assertEqual(base64.b64decode(self.internal_request.datas), img_byte)

    def test_doc_ctrl_upload_shortcut(self):
        self.authenticate(None, None)
        self.internal_file.action_update_access_rights(access_via_link="edit")
        for access_via_link, hidden in [
            ("none", True),
            ("view", True),
            ("edit", True),
            ("none", False),
            ("view", False),
        ]:
            with self.subTest(access_via_link=access_via_link, hidden=hidden):
                self.internal_file.action_update_access_rights(
                    access_via_link=access_via_link,
                    is_access_via_link_hidden=hidden,
                )
                res = self.url_open(
                    f"/documents/upload/{self.internal_shortcut.access_token}",
                    data={"csrf_token": http.Request.csrf_token(self)},
                    files={"ufile": ("hello.txt", BytesIO(b"Hello"), "text/plain")},
                    allow_redirects=False,
                )
                self.assertEqual(res.status_code, 404)

        self.internal_file.action_update_access_rights(
            access_via_link="edit",
            is_access_via_link_hidden=False,
        )
        res = self.url_open(
            f"/documents/upload/{self.internal_shortcut.access_token}",
            data={"csrf_token": http.Request.csrf_token(self)},
            files={"ufile": ("hello.txt", BytesIO(b"Hello"), "text/plain")},
            allow_redirects=False,
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, 303)
        self._assertPathIn(
            res.headers.get("Location"),
            {
                self.internal_file.access_url,
                self.internal_shortcut.access_url,
            },
        )
        self.assertEqual(self.internal_file.access_via_link, "edit")
        self.assertEqual(self.internal_file.name, "hello.txt")
        self.assertEqual(self.internal_file.mimetype, "text/plain")
        self.assertFalse(self.internal_file.res_id)
        self.assertFalse(self.internal_file.res_model)
        self.assertEqual(self.internal_file.attachment_id.res_id, self.internal_file.id)
        self.assertEqual(
            self.internal_file.attachment_id.res_model, "document.document"
        )
        self.assertEqual(self.internal_file.raw, b"Hello")
        tracking_message_ids = self.internal_file.message_ids.filtered(
            "tracking_value_ids"
        )
        self.assertTracking(
            tracking_message_ids,
            [
                ("name", "char", "internal-file.png", "hello.txt"),
            ],
            strict=True,
        )
        other_message_ids = self.internal_file.message_ids - tracking_message_ids
        self.assertEqual(
            other_message_ids.mapped("body"),
            [
                "<p>Document uploaded by Public user</p>",
                "<p>Document created</p>",
            ],
        )

        self.url_open(res.headers["Location"]).raise_for_status()

    def test_doc_ctrl_zip(self):
        self.authenticate("demo", "demo")
        res = self.url_open(
            "/documents/zip?"
            + urlencode(
                {
                    "zip_name": "file.zip",
                    "file_ids": f"{self.public_file.id},{self.internal_file.id}",
                }
            )
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("Content-Disposition"),
            "attachment; filename*=UTF-8''file.zip",
        )
        with BytesIO(res.content) as resfile, zipfile.ZipFile(resfile) as reszip:
            self.assertEqual(
                sorted(reszip.namelist()), ["internal-file.png", "public-file.png"]
            )
            self.assertEqual(reszip.read("internal-file.png"), self.doc_icon)
            self.assertEqual(reszip.read("public-file.png"), self.doc_icon)

        self.authenticate("portal_test", "portal_test")
        with self.assertLogs("odoo.http", "WARNING"):
            res = self.url_open(
                "/documents/zip?"
                + urlencode(
                    {
                        "zip_name": "file.zip",
                        "file_ids": f"{self.public_file.id},{self.internal_file.id}",
                    }
                )
            )
            self.assertEqual(res.status_code, HTTPStatus.FORBIDDEN)
        res = self.url_open(
            "/documents/zip?"
            + urlencode(
                {
                    "zip_name": "file.zip",
                    "file_ids": f"{self.public_file.id}",
                }
            )
        )
        res.raise_for_status()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("Content-Disposition"),
            "attachment; filename*=UTF-8''file.zip",
        )
        with BytesIO(res.content) as resfile, zipfile.ZipFile(resfile) as reszip:
            self.assertEqual(reszip.namelist(), ["public-file.png"])
            self.assertEqual(reszip.read("public-file.png"), self.doc_icon)

    def test_web_ctrl_documents(self):
        public_url = f"/web/content/document.document/{self.public_file.id}/raw"
        internal_url = f"/web/content/document.document/{self.internal_file.id}/raw"

        with self.subTest(user=None):
            self.authenticate(None, None)
            res = self.url_open(public_url)
            self.assertEqual(res.status_code, 404)

        with self.subTest(user="portal_test"):
            self.authenticate("portal_test", "portal_test")

            res = self.url_open(public_url)
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.content, self.doc_icon)

            res = self.url_open(internal_url)
            self.assertEqual(res.status_code, 404)

            self.internal_file.access_ids.filtered(
                lambda access: access.partner_id == self.user_portal.partner_id
            ).role = "view"
            res = self.url_open(internal_url)
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.content, self.doc_icon)

        with self.subTest(user="demo"):
            self.authenticate("demo", "demo")
            res = self.url_open(internal_url)
            res.raise_for_status()
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.content, self.doc_icon)

    def test_documents_get_init_data(self):
        shared_portal_values = {
            "access_ids": [
                Command.create(
                    {"partner_id": self.user_portal.partner_id.id, "role": "view"}
                )
            ]
        }
        shared_manager_values = {
            "access_ids": [
                Command.create(
                    {"partner_id": self.user_manager.partner_id.id, "role": "edit"}
                )
            ]
        }
        internal_folder = self.env["document.document"].create(
            [
                {"type": "folder", "name": "Internal", "access_internal": "edit"},
            ]
        )
        doc_as_demo = self.env["document.document"].with_user(self.user_demo)
        restricted_folder = doc_as_demo.create(
            {
                "folder_id": internal_folder.id,
                "type": "folder",
                "name": "Restricted Folder",
                "access_internal": "none",
            }
        )
        (
            demo_personal,
            company_portal,
            company_child_portal,
            restricted_portal,
            restricted_manager,
            shared_via_link,
        ) = doc_as_demo.create(
            [
                shared_portal_values | {"name": "demo_personal_share_portal"},
                shared_portal_values | {"name": "company_share_portal"},
                shared_portal_values
                | {
                    "name": "company_child_share_portal",
                    "folder_id": internal_folder.id,
                },
                shared_portal_values
                | {
                    "name": "restricted_share_portal",
                    "folder_id": restricted_folder.id,
                },
                shared_manager_values
                | {"name": "restricted_manager", "folder_id": restricted_folder.id},
                {
                    "name": "restricted_shared_link",
                    "folder_id": restricted_folder.id,
                    "access_via_link": "view",
                },
            ]
        )
        (internal_folder | company_portal).sudo().user_folder_id = "COMPANY"
        archived_doc, archived_folder = archived = doc_as_demo.create(
            [
                {"type": doc_type, "name": f"Archived {doc_type}"}
                for doc_type in ("binary", "folder")
            ]
        )
        archived_doc_shortcut, archived_folder_shortcut = (
            archived.action_create_shortcut()
        )
        archived.action_archive()

        for user in (self.user_portal, self.user_manager):
            ShareRoute._upsert_last_access_date(self.env(user=user), shared_via_link)

        for document, user, expected_folder_id, expected_document_id in [
            (demo_personal, self.user_demo, "MY", demo_personal.id),
            (demo_personal, self.user_portal, False, demo_personal.id),
            (demo_personal, self.user_manager, False, demo_personal.id),
            (
                company_portal,
                self.user_demo,
                "COMPANY",
                company_portal.id,
            ),
            (company_portal, self.user_portal, False, company_portal.id),
            (
                company_child_portal,
                self.user_demo,
                internal_folder.id,
                company_child_portal.id,
            ),
            (company_child_portal, self.user_portal, False, company_child_portal.id),
            (
                company_child_portal,
                self.user_manager,
                internal_folder.id,
                company_child_portal.id,
            ),
            (
                restricted_portal,
                self.user_demo,
                restricted_folder.id,
                restricted_portal.id,
            ),
            (restricted_portal, self.user_portal, False, restricted_portal.id),
            (
                restricted_manager,
                self.user_demo,
                restricted_folder.id,
                restricted_manager.id,
            ),
            (restricted_manager, self.user_manager, "SHARED", restricted_manager.id),
            (shared_via_link, self.user_portal, False, shared_via_link.id),
            (shared_via_link, self.user_manager, "SHARED", shared_via_link.id),
            (archived_doc, self.user_demo, "TRASH", archived_doc.id),
            (archived_folder, self.user_demo, "TRASH", archived_folder.id),
            (archived_doc_shortcut, self.user_demo, "MY", archived_doc_shortcut.id),
            (
                archived_folder_shortcut,
                self.user_demo,
                "MY",
                archived_folder_shortcut.id,
            ),
            (internal_folder, self.user_demo, internal_folder.id, None),
        ]:
            document.invalidate_recordset()
            with self.subTest(document_name=document.name, username=user.name):
                data = ShareRoute._documents_get_init_data(
                    document.with_user(user), user
                )
                self.assertEqual(
                    data["user_folder_id"],
                    str(expected_folder_id)
                    if expected_folder_id
                    else expected_folder_id,
                )
                self.assertEqual(data.get("document_id"), expected_document_id)

    def test_from_access_token(self):
        url = self.env["document.document"].create(
            {"name": "url", "type": "url", "url": "https://www.odoo.com/"}
        )
        access_token = url.access_token
        url.unlink()
        self.authenticate("admin", "admin")
        res = self.url_open(
            f"/documents/touch/{access_token}",
            data=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"jsonrpc": "2.0", "id": None, "result": {}})

    def test_touch_logs_access_on_an_archived_document(self):
        document = self.env["document.document"].create(
            {
                "name": "archived",
                "type": "url",
                "url": "https://www.odoo.com/",
                "access_via_link": "view",
            }
        )
        document.action_archive()
        partner = self.user_demo.partner_id
        domain = [
            ("document_id", "=", document.id),
            ("partner_id", "=", partner.id),
        ]
        self.env["document.access"].search(domain).unlink()

        self.authenticate("demo", "demo")
        res = self.url_open(
            f"/documents/touch/{document.access_token}",
            data=json.dumps({}),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            self.env["document.access"].search(domain),
            "touching an archived document must log the access",
        )

    def test_non_ascii_access_token_is_not_a_500(self):
        document = self.env["document.document"].create(
            {"name": "tok", "type": "url", "url": "https://www.odoo.com/"}
        )
        suffix = document.access_token.rpartition("o")[2]
        for route in ("/documents", "/documents/content", "/documents/thumbnail"):
            for token in (f"éo{suffix}", f"你好o{suffix}"):
                with self.subTest(route=route, token=token):
                    res = self.url_open(f"{route}/{token}", allow_redirects=False)
                    self.assertNotEqual(
                        res.status_code, 500, "non-ASCII token must not 500"
                    )
        res = self.url_open(f"/documents/XXXo{suffix}", allow_redirects=False)
        self.assertEqual(res.status_code, 404)

    def test_upload_rejects_unvalidated_field_values(self):
        uploader = mail_new_test_user(
            self.env,
            login="upload_probe",
            password="upload_probe",
            groups="base.group_user,document.group_documents_user",
        )
        folder = self.env["document.document"].create(
            {
                "name": "Shared upload folder",
                "type": "folder",
                "access_via_link": "edit",
                "access_internal": "none",
            }
        )
        self.authenticate("upload_probe", "upload_probe")
        url = f"/documents/upload/{folder.access_token}"

        def upload(**extra):
            return self.url_open(
                url,
                data={"csrf_token": http.Request.csrf_token(self), **extra},
                files={"ufile": ("probe.txt", b"hi", "text/plain")},
                allow_redirects=False,
            )

        other = self.env.ref("base.user_admin")
        self.assertEqual(upload(owner_id=str(other.id)).status_code, 403)
        self.assertEqual(upload(res_model="res.company", res_id="1").status_code, 403)
        self.assertEqual(upload(res_model="bogus.model", res_id="1").status_code, 400)
        res = upload()
        self.assertEqual(res.status_code, 200)
        document = self.env["document.document"].search(
            [("folder_id", "=", folder.id), ("name", "=", "probe.txt")], limit=1
        )
        self.assertEqual(document.owner_id, uploader)

    def test_shared_folder_download_is_not_empty_for_logged_in_visitors(self):
        folder = self.env["document.document"].create(
            {
                "name": "Shared folder",
                "type": "folder",
                "access_via_link": "view",
                "access_internal": "none",
            }
        )
        self.env["document.document"].create(
            {
                "name": "shared_child.txt",
                "type": "binary",
                "datas": TEXT,
                "folder_id": folder.id,
                "access_via_link": "view",
            }
        )
        self.env["document.document"].create(
            {
                "name": "hidden_child.txt",
                "type": "binary",
                "datas": TEXT,
                "folder_id": folder.id,
                "access_via_link": "none",
            }
        )
        portal = mail_new_test_user(
            self.env,
            login="zip_portal",
            password="zip_portal",
            groups="base.group_portal",
        )
        internal = mail_new_test_user(
            self.env,
            login="zip_internal",
            password="zip_internal",
            groups="base.group_user,document.group_documents_user",
        )
        url = f"/documents/content/{folder.access_token}"

        def entries():
            res = self.url_open(url, allow_redirects=False)
            self.assertEqual(res.status_code, 200)
            return zipfile.ZipFile(BytesIO(res.content)).namelist()

        self.assertEqual(entries(), ["shared_child.txt"], "anonymous visitor")
        for user in (portal, internal):
            self.authenticate(user.login, user.login)
            self.assertEqual(
                entries(), ["shared_child.txt"], f"{user.login} follows the same link"
            )

    def test_upload_internal_multi_company_defaults(self):
        main_company = self.env.ref("base.main_company")
        comp = self.env["res.company"].create({"name": "Company 2"})
        company_field = self.env["ir.model.fields"].search(
            [("model", "=", "document.document"), ("name", "=", "company_id")], limit=1
        )
        self.env["ir.default"].create(
            [
                {
                    "field_id": company_field.id,
                    "company_id": comp.id,
                    "json_value": comp.id,
                },
                {
                    "field_id": company_field.id,
                    "company_id": main_company.id,
                    "json_value": main_company.id,
                },
            ]
        )

        self.user_admin.write({"company_ids": [Command.link(comp.id)]})
        self.assertGreaterEqual(self.user_admin.company_ids, main_company | comp)

        self.authenticate("admin", "admin")
        with RecordCapturer(self.env["document.document"], []) as record_capture:
            res = self.url_open(
                "/documents/upload",
                data={
                    "csrf_token": http.Request.csrf_token(self),
                    "allowed_company_ids": f"[{comp.id}]",
                    "user_folder_id": "COMPANY",
                },
                files={"ufile": ("testingfile.txt", BytesIO(b"Hello"), "text/plain")},
                allow_redirects=False,
            )
            res.raise_for_status()
        document1 = record_capture.records.check_singleton()
        self.assertEqual(document1.company_id, comp)

        with RecordCapturer(self.env["document.document"], []) as record_capture:
            res = self.url_open(
                "/documents/upload",
                data={
                    "csrf_token": http.Request.csrf_token(self),
                    "allowed_company_ids": f"[{main_company.id}]",
                    "user_folder_id": "COMPANY",
                },
                files={"ufile": ("testingfile2.txt", BytesIO(b"Hello2"), "text/plain")},
                allow_redirects=False,
            )
            res.raise_for_status()
        document2 = record_capture.records.check_singleton()
        self.assertEqual(document2.company_id, main_company)

    def test_custom_mimetype_content_routes(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "An Email without attachment",
                "type": "binary",
                "raw": "<p>A mail body</p>",
                "mimetype": "application/documents-email",
                "res_model": "document.document",
            }
        )
        document = self.env["document.document"].create(
            {
                "name": "An Email without attachment",
                "access_internal": "edit",
                "access_via_link": "view",
                "owner_id": self.user_admin.id,
                "folder_id": self.public_folder.id,
                "attachment_id": attachment.id,
            }
        )
        self.authenticate("admin", "admin")
        urls = (
            f"/documents/content/{document.access_token}",
            f"/web/content/document.document/{document.id}/raw",
            f"/web/content/{attachment.id}",
        )
        for url in urls:
            res = self.url_open(f"{url}?download=0")
            self.assertEqual(res.content, b"<p>A mail body</p>")
            self.assertEqual(
                res.headers.get("Content-Type"), "text/plain; charset=utf-8"
            )
            self.assertTrue(
                "inline;" in res.headers.get("Content-Disposition"),
                "attachment is displayed as plain text in browser.",
            )
            res = self.url_open(f"{url}?download=1")
            self.assertTrue(
                "attachment;" in res.headers.get("Content-Disposition"),
                "attachment is downloaded",
            )

    def test_upload_traceback(self):
        url = "/documents/upload_traceback"
        self.authenticate("admin", "admin")
        with RecordCapturer(self.env["document.document"], []) as capture:
            res = self.url_open(
                url,
                data={"csrf_token": http.Request.csrf_token(self)},
                files={
                    "ufile": (
                        "TEST_traceback.txt",
                        BytesIO(b"TEST traceback"),
                        "text/plain",
                    )
                },
            )
            res.raise_for_status()
            self.assertEqual(
                res.headers["Content-Type"], "application/json; charset=utf-8"
            )
            self.assertRegex(res.json()[0], r"^https?://.*/odoo/documents/")
            res = self.url_open(
                url,
                data={"csrf_token": http.Request.csrf_token(self)},
                files={
                    "ufile": (
                        "TEST_traceback2.txt",
                        BytesIO(b"TEST traceback"),
                        "text/plain",
                    )
                },
            )
            res.raise_for_status()
            self.assertEqual(
                res.headers["Content-Type"], "application/json; charset=utf-8"
            )
            self.assertRegex(res.json()[0], r"^https?://.*/odoo/documents/")
        documents = capture.records
        self.assertEqual(len(documents), 3)
        self.assertEqual(documents[0].type, "folder")
        self.assertEqual(documents[0].name, "Support")
        self.assertEqual(documents[1].type, "binary")
        self.assertEqual(documents[1].name, "TEST_traceback.txt")
        self.assertEqual(documents[1].mimetype, "text/plain")
        self.assertEqual(documents[1].raw, b"TEST traceback")
        self.assertEqual(documents[1].folder_id, documents[0])
        self.assertEqual(documents[2].type, "binary")
        self.assertEqual(documents[2].name, "TEST_traceback2.txt")
        self.assertEqual(documents[2].mimetype, "text/plain")
        self.assertEqual(documents[2].raw, b"TEST traceback")
        self.assertEqual(documents[2].folder_id, documents[0])


@tagged("post_install", "-at_install")
class TestCaseSecurityRoutes(HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()

        self.raw_gif = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
        pdf_buffer = BytesIO()
        canva = canvas.Canvas(pdf_buffer, pagesize=(600, 800))
        canva.drawString(100, 750, "Minimal PDF")
        canva.save()
        self.raw_pdf = b64encode(pdf_buffer.getvalue())

        (
            self.user_attachment_gif,
            self.admin_attachment_gif,
            self.user_attachment_pdf,
            self.admin_attachment_pdf,
        ) = self.env["ir.attachment"].create(
            [
                {
                    "datas": self.raw_gif,
                    "name": "attachmentGif_A.gif",
                    "res_model": False,
                    "res_id": False,
                },
                {
                    "datas": self.raw_gif,
                    "name": "attachmentGif_B.gif",
                    "res_model": False,
                    "res_id": False,
                },
                {
                    "datas": self.raw_pdf,
                    "name": "attachmentPdf_A.pdf",
                    "mimetype": "application/pdf",
                    "res_model": False,
                    "res_id": False,
                },
                {
                    "datas": self.raw_pdf,
                    "name": "attachmentPdf_B.pdf",
                    "mimetype": "application/pdf",
                    "res_model": False,
                    "res_id": False,
                },
            ]
        )
        (
            self.user_document_gif,
            self.admin_document_gif,
            self.user_document_pdf,
            self.admin_document_pdf,
        ) = self.env["document.document"].create(
            [
                {
                    "name": "GIF A",
                    "attachment_id": self.user_attachment_gif.id,
                },
                {
                    "name": "GIF B",
                    "attachment_id": self.admin_attachment_gif.id,
                },
                {
                    "name": "PDF A",
                    "attachment_id": self.user_attachment_pdf.id,
                },
                {
                    "name": "PDF B",
                    "attachment_id": self.admin_attachment_pdf.id,
                },
            ]
        )
        self.document_user = self.env["res.users"].create(
            {
                "name": "user",
                "login": "user",
                "password": "useruser",
                "email": "user@yourcompany.com",
                "group_ids": [(6, 0, [self.ref("document.group_documents_user")])],
            }
        )

    @mute_logger("odoo.http")
    def test_documents_zip_access(self):
        self.authenticate("user", "useruser")
        response = self.url_open(
            "/documents/zip",
            data={
                "file_ids": ",".join(
                    map(str, [self.user_document_gif.id, self.admin_document_gif.id])
                ),
                "zip_name": "testZip.zip",
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"admin_document", response.content)

    @mute_logger("odoo.http", "odoo.addons.document.controllers.document")
    def test_documents_zip_size_limit(self):
        own_documents = self.env["document.document"].create(
            [
                {
                    "name": "Own A",
                    "attachment_id": self.user_attachment_pdf.copy().id,
                    "owner_id": self.document_user.id,
                },
                {
                    "name": "Own B",
                    "attachment_id": self.admin_attachment_pdf.copy().id,
                    "owner_id": self.document_user.id,
                },
            ]
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "document.zip_max_file_count", "1"
        )
        self.authenticate("user", "useruser")
        response = self.url_open(
            "/documents/zip",
            data={
                "file_ids": ",".join(map(str, own_documents.ids)),
                "zip_name": "tooBig.zip",
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, 413)

    @mute_logger("odoo.http")
    def test_documents_split_access(self):
        self.authenticate("user", "useruser")
        response = self.url_open(
            "/documents/pdf_split",
            data={
                "vals": json.dumps(
                    {"tag_ids": [], "owner_id": self.document_user.id, "active": True}
                ),
                "new_files": json.dumps(
                    [
                        {
                            "name": "Test",
                            "new_pages": [
                                {
                                    "old_file_type": "document",
                                    "old_file_index": self.admin_document_pdf.id,
                                    "old_page_number": 1,
                                }
                            ],
                        }
                    ]
                ),
                "archive": False,
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, 403)
