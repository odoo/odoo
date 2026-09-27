# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from textwrap import dedent
from unittest import SkipTest
from unittest.mock import patch

try:
    from markdown2 import markdown
except ImportError:
    markdown = None

import odoo
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon
from odoo.http.stream import STATIC_CACHE_LONG


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestAttachmentController(MailControllerAttachmentCommon):
    def test_independent_attachment_delete(self):
        """Test access to delete an attachment whether or not limited `ownership_token` is sent"""
        self._execute_subtests_delete(self.all_users, token=True, allowed=True)
        self._execute_subtests_delete(self.user_admin, token=False, allowed=True)
        self._execute_subtests_delete(
            (self.guest, self.user_employee, self.user_portal, self.user_public),
            token=False,
            allowed=False,
        )

    def test_attachment_delete_linked_to_thread(self):
        """Test access to delete an attachment associated with a thread
        whether or not limited `ownership_token` is sent"""
        thread = self.env["mail.test.simple"].create({"name": "Test"})
        self._execute_subtests_delete(self.all_users, token=True, allowed=True, thread=thread)
        self._execute_subtests_delete(
            (self.user_admin, self.user_employee),
            token=False,
            allowed=True,
            thread=thread,
        )
        self._execute_subtests_delete(
            (self.guest, self.user_portal, self.user_public),
            token=False,
            allowed=False,
            thread=thread,
        )

    def test_attachment_delete_kept_on_message(self):
        """Test that trimming the attachment list of a thread doesn't remove the
        files from the message they were posted on, with the write access on the
        attachment as well as with an `ownership_token` alone"""
        thread = self.env["mail.test.simple"].create({"name": "Test"})
        attachments = self.env["ir.attachment"].create([
            {"name": "sample attachment", "res_id": thread.id, "res_model": thread._name},
            {"name": "other attachment", "res_id": thread.id, "res_model": thread._name},
        ])
        messages = [
            thread.message_post(body="Sample", attachment_ids=attachment.ids)
            for attachment in attachments
        ]
        users = (self.user_admin, self.user_portal)
        for attachment, message, user in zip(attachments, messages, users):
            with self.subTest(user=user.name):
                self.authenticate(user.login, user.login)
                self.make_jsonrpc_request(
                    route="/mail/attachment/delete",
                    params={
                        "access_token_by_attachment_id": {
                            attachment.id: attachment._get_ownership_token(),
                        },
                        "keep_on_messages": True,
                    },
                )
                self.env.invalidate_all()
                self.assertEqual(attachment.res_model, "mail.message")
                self.assertEqual(attachment.res_id, message.id)
                self.assertIn(attachment, message.attachment_ids)
                self.assertNotIn(attachment, thread._get_mail_thread_data_attachments())
                self.assertNotIn("o-mail-Message-edited", message.body)

    def test_upload_multi_company(self):
        record = self.user_employee.partner_id
        record.company_id = self.user_employee.company_id
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.assertTrue(record.company_id)  # Ensure the thread has a company
        test_cases = [
            ({}, self.user_employee.company_id),
            (
                {
                    "cookies": {
                        "cids": f"{self.company_2.id}-{self.company_3.id}",
                    },
                },
                self.company_2,
            ),
            (
                {
                    "cookies": {
                        "cids": f"{self.company_2.id}-{self.user_admin.company_id.id}",
                    },
                },
                self.user_admin.company_id,
            ),
        ]
        for kwargs, expected_company in test_cases:
            with self.subTest(expected_company=expected_company):
                record.company_id = False if kwargs else record.company_id
                attachment = self.env["ir.attachment"].browse(
                    self._upload_attachment(record, kwargs)
                )
                self.assertEqual(attachment.company_id, expected_company)

    def test_attachment_render_text_headers(self):
        """Test cache control, content-type, and security headers for text rendering."""
        strict_csp = "default-src 'none'; sandbox;"
        render_csp = "default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self'; sandbox;"

        attachments = self.env["ir.attachment"].create([
            {
                "name": "test.html",
                "mimetype": "text/html",
                "raw": b"<h1>Hello HTML</h1>",
                "res_model": "res.partner",
                "res_id": self.user_admin.partner_id.id,
            },
            {
                "name": "test.md",
                "mimetype": "text/markdown",
                "raw": b"# Hello Markdown",
                "res_model": "res.partner",
                "res_id": self.user_admin.partner_id.id,
            },
            {
                "name": "test.txt",
                "mimetype": "text/plain",
                "raw": b'Hello Plain Text',
                "res_model": "res.partner",
                "res_id": self.user_admin.partner_id.id,
            },
            {
                "name": "test.json",
                "mimetype": "application/json",
                "raw": b'{"key": "value"}',
                "res_model": "res.partner",
                "res_id": self.user_admin.partner_id.id,
            },
        ])
        attachments.generate_access_token()
        html_attachment, md_attachment, txt_attachment, json_attachment = attachments

        # HTML: Always streamed in full with strict CSP
        html_cases = [
            (html_attachment, head, unique, "text/html; charset=utf-8", strict_csp)
            for head in (False, True) for unique in (False, True)
        ]
        # JSON: Full file streams (strict CSP), preview renders (permissive CSP)
        json_cases = [
            (json_attachment, head, unique,
            "text/html; charset=utf-8" if head else "application/json", render_csp if head else strict_csp)
            for head in (False, True) for unique in (False, True)
        ]
        # Markdown & Plain Text: Always rendered to HTML with permissive CSP.
        # Note: txt_attachment acts as a representative for all other SUPPORTED_TEXT_MIMETYPES
        # (text/xml, text/css, text/csv, application/javascript, etc.) since they share this code path.
        rendered_cases = [
            (attachment, head, unique, "text/html; charset=utf-8", render_csp)
            for attachment in (md_attachment, txt_attachment)
            for head in (False, True) for unique in (False, True)
        ]
        test_cases = html_cases + json_cases + rendered_cases

        for attachment, head, unique, expected_content_type, expected_csp in test_cases:
            with self.subTest(attachment=attachment.name, head=head, unique=unique):
                url = f"/mail/attachment/render_text/{attachment.id}?access_token={attachment.access_token}"
                if head:
                    url += "&head=1"
                if unique:
                    url += f"&unique={attachment.checksum}"
                res = self.url_open(url)
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.headers.get("Content-Type"), expected_content_type)
                self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
                self.assertEqual(res.headers.get("Content-Security-Policy"), expected_csp)
                cache_control = res.headers.get("Cache-Control", "")
                self.assertNotIn("public", cache_control)
                self.assertIn("private", cache_control)
                if unique:
                    self.assertIn("immutable", cache_control)
                    self.assertIn(f"max-age={STATIC_CACHE_LONG}", cache_control)
                else:
                    self.assertNotIn("immutable", cache_control)
                    self.assertNotIn("max-age", cache_control)

    def test_attachment_render_text_html(self):
        """Check that HTML is streamed in full, and that HTML from non-admins is escaped."""
        # HTML created by admin is sent as HTML
        attachment_admin = self.env['ir.attachment'].create({
            'name': 'Test HTML.html',
            'raw': b"<b>test HTML</b>" + b"_" * 1024 + b"end of HTML",
            'res_model': 'res.partner',
            'res_id': self.user_admin.partner_id.id,
            'mimetype': 'text/html',
        })
        attachment_admin.generate_access_token()
        url_admin = f"/mail/attachment/render_text/{attachment_admin.id}?access_token={attachment_admin.access_token}"
        with patch.object(AttachmentController, 'TEXTUAL_THUMBNAIL_SIZE', 1024):
            res = self.url_open(url_admin)
        self.assertEqual(res.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertIn('<b>test HTML</b>', res.text)
        self.assertNotIn('white-space: pre-wrap', res.text)
        self.assertIn('end of HTML', res.text)
        # It's not truncated for thumbnails to avoid breaking HTML markup
        with patch.object(AttachmentController, 'TEXTUAL_THUMBNAIL_SIZE', 1024):
            res = self.url_open(f"{url_admin}&head=1")
        self.assertEqual(res.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertIn('<b>test HTML</b>', res.text)
        self.assertNotIn('white-space: pre-wrap', res.text)
        self.assertIn('end of HTML', res.text, 'HTML is not truncated')
        # Check that HTML created by non-admins (e.g., employee) is escaped
        attachment_user = self.env['ir.attachment'].with_user(self.user_employee).create({
            'name': 'Test HTML Demo.html',
            'raw': b"<b>test HTML</b>" + b"_" * 1024 + b"end of HTML",
            'res_model': 'res.partner',
            'res_id': self.user_employee.partner_id.id,
            'mimetype': 'text/html',
        })
        attachment_user.generate_access_token()
        self.assertEqual(attachment_user.mimetype, "text/plain")
        url_demo = f"/mail/attachment/render_text/{attachment_user.id}?access_token={attachment_user.access_token}"
        for head in (0, 1):
            res = self.url_open(f"{url_demo}&head={head}")
            self.assertEqual(res.headers['Content-Type'], 'text/html; charset=utf-8')
            self.assertIn('&lt;b&gt;test HTML&lt;/b&gt;', res.text, 'HTML from non-admin must be escaped')
            self.assertIn('white-space: pre-wrap', res.text)

    def test_attachment_render_text_json(self):
        """Check that JSON is served as application/json, but truncated to HTML for thumbnails."""
        content = json.dumps({"a": 1337, "_" * 1024: "end of json"})
        attachment = self.env['ir.attachment'].create({
            'name': 'Test Json.json',
            'raw': content.encode(),
            'res_model': 'res.partner',
            'res_id': self.user_admin.partner_id.id,
            'mimetype': 'application/json',
        })
        attachment.generate_access_token()
        url = f"/mail/attachment/render_text/{attachment.id}?access_token={attachment.access_token}"

        # JSON is sent as json, so it is rendered by the browser natively
        with patch.object(AttachmentController, 'TEXTUAL_THUMBNAIL_SIZE', 1024):
            res = self.url_open(url)
        self.assertEqual(res.headers['Content-Type'], 'application/json')
        self.assertIn('1337', res.text)
        self.assertIn('end of json', res.text)
        # The head of JSON is truncated and uses the "textual" HTML template
        with patch.object(AttachmentController, 'TEXTUAL_THUMBNAIL_SIZE', 1024):
            res = self.url_open(f"{url}&head=1")
        self.assertEqual(res.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertIn('1337', res.text)
        self.assertIn('white-space: pre-wrap', res.text)
        self.assertNotIn('end of json', res.text)

    def test_attachment_render_text_markdown(self):
        """Markdown is rendered, escaped, sanitized, and stripped of every link."""
        if not markdown:
            raise SkipTest("markdown2 not installed, cannot run this test")
        content = dedent("""
            # Title
            <span class="testStripClass" style="color: red;">Test</span>
            <script>console.log('xssScriptTest')</script>
            <b onclick="console.log('xssEventTest')">Malicious</b>
            [Odoo](https://odoo.com) and [ref][1] and <https://auto.test>
            [1]: https://ref.test
            ```py
            def test():
                pass
            ```
        """)
        content += "\n" + "x" * 1024 + "end of markdown"
        attachment = self.env["ir.attachment"].create({
            "name": "Test Markdown.md",
            "mimetype": "text/markdown",
            "raw": content.encode(),
            "res_model": "res.partner",
            "res_id": self.user_admin.partner_id.id,
        })
        attachment.generate_access_token()
        url = f"/mail/attachment/render_text/{attachment.id}?access_token={attachment.access_token}"
        for head in (False, True):
            with self.subTest(head=head), patch.object(AttachmentController, "TEXTUAL_THUMBNAIL_SIZE", 1024):
                res = self.url_open(f"{url}&head=1" if head else url)
                self.assertEqual(res.status_code, 200)
                self.assertIn("<h1>", res.text)
                self.assertNotIn("```", res.text, "code blocks are rendered")
                self.assertIn("&lt;span class=", res.text)
                self.assertIn("&lt;script&gt;", res.text)
                self.assertIn("&lt;b onclick=", res.text)
                self.assertNotIn("<script", res.text, "no script tag is ever parsed")
                self.assertNotIn("<a", res.text)
                self.assertIn("Odoo (https://odoo.com)", res.text)
                self.assertIn("ref (https://ref.test)", res.text)
                self.assertIn("https://auto.test (https://auto.test)", res.text)
                if head:
                    self.assertNotIn("end of markdown", res.text, "thumbnail is truncated")
                else:
                    self.assertIn("end of markdown", res.text, "full document is present")

    def test_attachment_thumbnail_textual_size(self):
        """Test that large plain text files are properly truncated when requested as a thumbnail."""
        attachment = self.env['ir.attachment'].create({
            'name': 'Long Text File.txt',
            'raw': b"A" * 3000,
            'res_model': 'res.partner',
            'res_id': self.user_admin.partner_id.id,
            'mimetype': 'text/plain',
        })
        attachment.generate_access_token()
        TESTING_SIZE = 2000
        self.assertGreater(attachment.raw.size, TESTING_SIZE)
        url = f"/mail/attachment/render_text/{attachment.id}?access_token={attachment.access_token}&head=1"
        with patch.object(AttachmentController, 'TEXTUAL_THUMBNAIL_SIZE', 1024):
            res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn('<pre style="white-space: pre-wrap', res.text)
        self.assertLess(len(res.content), TESTING_SIZE)
