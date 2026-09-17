import base64
import io
import json

from PIL import Image

from odoo import Command, http
from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger

from .test_document_common import TransactionCaseDocuments


def _png(color):
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), color).save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue())


@tagged("post_install", "-at_install")
class TestDocumentsThumbnail(TransactionCaseDocuments):
    def test_thumbnail_survives_a_web_save(self):
        document = self.env["document.document"].create(
            {"name": "pic.png", "type": "binary", "datas": _png((10, 200, 10))}
        )
        self.assertEqual(document.thumbnail_status, "present")
        self.assertTrue(document.thumbnail)

        result = document.web_save(
            {"datas": _png((10, 10, 200))}, {"thumbnail_status": {}}
        )

        self.assertEqual(result[0]["thumbnail_status"], "present")
        document.invalidate_recordset()
        self.assertEqual(document.thumbnail_status, "present")
        self.assertTrue(document.thumbnail)

    def test_thumbnail_recompute_under_bin_size(self):
        document = self.env["document.document"].create(
            {"name": "pic.png", "type": "binary", "datas": _png((200, 30, 30))}
        )
        self.env.flush_all()
        self.env.invalidate_all()
        for field_name in ("thumbnail", "thumbnail_status"):
            self.env.add_to_compute(
                self.env["document.document"]._fields[field_name], document
            )

        self.assertEqual(
            document.with_context(bin_size=True).thumbnail_status, "present"
        )
        self.env.flush_all()
        document.invalidate_recordset()
        self.assertTrue(document.thumbnail)

    def test_thumbnail_status_error_for_undecodable_content(self):
        document = self.env["document.document"].create(
            {
                "name": "not-an-image.png",
                "type": "binary",
                "datas": base64.b64encode(b"certainly not a png"),
            }
        )
        document.attachment_id.sudo().mimetype = "image/png"
        document.invalidate_recordset()
        self.assertEqual(document.thumbnail_status, "error")
        self.assertFalse(document.thumbnail)


@tagged("post_install", "-at_install")
class TestDocumentsThumbnailRoutes(HttpCase, TransactionCaseDocuments):
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

    def _post_thumbnail(self, payload):
        return self.url_open(
            f"/documents/document/{self.webp.id}/update_thumbnail",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {"document_id": self.webp.id, "thumbnail": payload},
                }
            ),
        ).json()

    def test_s3_thumbnail_rejects_non_image(self):
        """Payload validation, driven by a principal allowed to store one.

        This used to authenticate as the VIEWER, which passed only because the
        route checked read access before a `sudo()` write. Storing a thumbnail
        is a write on the document, so the audience is an editor; what a viewer
        gets is pinned by the test below.
        """
        self.authenticate("audit_mgr", "audit_mgr")
        garbage = base64.b64encode(b"<svg onload=alert(1)>NOTIMAGE").decode()
        body = self._post_thumbnail(garbage)
        self.assertIn("error", body)
        self.assertFalse(self.webp.thumbnail)
        buffer = io.BytesIO()
        Image.new("RGB", (48, 48)).save(buffer, format="PNG")
        body = self._post_thumbnail(base64.b64encode(buffer.getvalue()).decode())
        self.assertNotIn("error", body)
        self.assertTrue(self.webp.thumbnail)
        self.assertTrue(base64.b64decode(self.webp.thumbnail).startswith(b"\x89PNG"))

    def test_a_viewer_cannot_store_a_thumbnail(self):
        """A read check guarding a `sudo()` write let any reader set it.

        The thumbnail is stored on the document and shown to everyone, and the
        write flips `thumbnail_status` away from "client_generated" -- so the
        first reader to post one decided what every other user saw, and nobody
        could correct it afterwards.
        """
        self.authenticate("audit_view", "audit_view")
        buffer = io.BytesIO()
        Image.new("RGB", (48, 48)).save(buffer, format="PNG")

        body = self._post_thumbnail(base64.b64encode(buffer.getvalue()).decode())

        self.assertEqual(
            body.get("error", {}).get("data", {}).get("name"),
            "odoo.exceptions.AccessError",
        )
        self.webp.invalidate_recordset()
        self.assertFalse(self.webp.thumbnail)
        self.assertEqual(
            self.webp.thumbnail_status,
            "client_generated",
            "and the document stays open for someone who may store one",
        )


def _oversized_png(side):
    """A small payload that decodes to `side`x`side` pixels.

    A uniform image compresses to a few hundred KB however large its canvas,
    which is what makes the pixel count, not the byte count, the thing an
    upload limit fails to bound.
    """
    buffer = io.BytesIO()
    Image.new("L", (side, side)).save(buffer, "PNG")
    return buffer.getvalue()


@tagged("post_install", "-at_install")
class TestDocumentsThumbnailUndecodable(TransactionCaseDocuments):
    """`_compute_thumbnail` degrades; it never takes the transaction with it.

    The compute is stored and runs inside `create`/`write`, so an image PIL
    refuses to decode must land as `thumbnail_status = "error"`. Anything that
    escapes it aborts the write that carried the file -- including an upload
    arriving on the public `/documents/upload` route through an edit link.
    """

    def _create_with_content(self, name, raw, mimetype):
        attachment = (
            self.env["ir.attachment"]
            .with_context(no_document=True)
            .create({"name": name, "raw": raw, "mimetype": mimetype})
        )
        return self.env["document.document"].create(
            {"name": name, "type": "binary", "attachment_id": attachment.id}
        )

    def test_a_decompression_bomb_is_an_error_thumbnail_not_a_traceback(self):
        # 16000x16000 = 256 Mpx, past PIL's 89 Mpx MAX_IMAGE_PIXELS doubled,
        # so Image.open raises DecompressionBombError -- neither UserError nor
        # TypeError, the only two the compute used to catch.
        document = self._create_with_content(
            "bomb.png", _oversized_png(16000), "image/png"
        )
        self.env.flush_all()

        self.assertEqual(document.thumbnail_status, "error")
        self.assertFalse(document.thumbnail)
        self.assertTrue(
            document.attachment_id,
            "the file is still stored; only its preview failed",
        )

    def test_undecodable_bytes_claiming_to_be_an_image(self):
        document = self._create_with_content(
            "claims.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 512, "image/png"
        )
        self.env.flush_all()

        self.assertEqual(document.thumbnail_status, "error")
        self.assertFalse(document.thumbnail)

    def test_a_decodable_image_still_gets_its_thumbnail(self):
        """The negative control: widening the handler must not swallow success."""
        document = self._create_with_content(
            "fine.png", base64.b64decode(_png((10, 200, 10))), "image/png"
        )
        self.env.flush_all()

        self.assertEqual(document.thumbnail_status, "present")
        self.assertTrue(document.thumbnail)


@tagged("post_install", "-at_install")
class TestDocumentsThumbnailPublicUpload(HttpCase):
    """The bomb reaches the compute through the PUBLIC upload route.

    The unit test above proves `_compute_thumbnail` degrades; this one proves
    the input is reachable without an account. Together they are the claim:
    an unauthenticated visitor holding an edit link -- the shape
    `document.request_wizard` creates for a requestee with no user -- can send
    a payload that used to answer 500 and lose the upload.
    """

    def _request_document(self):
        return self.env["document.document"].create(
            {
                "name": "please-upload-here.txt",
                "type": "binary",
                "access_via_link": "edit",
            }
        )

    def _upload(self, document, filename, payload):
        return self.url_open(
            f"/documents/upload/{document.access_token}",
            data={"csrf_token": http.Request.csrf_token(self)},
            files={"ufile": (filename, io.BytesIO(payload), "image/png")},
        )

    @mute_logger(
        "odoo.http",
        "odoo.sql_db",
        "odoo.addons.document.models.document_document",
    )
    def test_an_unauthenticated_visitor_may_upload_an_undecodable_image(self):
        self.authenticate(None, None)
        document = self._request_document()
        buffer = io.BytesIO()
        # 16000x16000 = 256 Mpx, past PIL's MAX_IMAGE_PIXELS doubled.
        Image.new("L", (16000, 16000)).save(buffer, "PNG")
        payload = buffer.getvalue()
        self.assertLess(
            len(payload),
            300 * 1024,
            "small on the wire is the point: no upload size limit bounds the "
            "pixel count",
        )

        response = self._upload(document, "bomb.png", payload)

        self.assertEqual(response.status_code, 200)
        document.invalidate_recordset()
        self.assertTrue(document.attachment_id, "the file is stored")
        self.assertEqual(document.mimetype, "image/png")
        self.assertEqual(document.thumbnail_status, "error")

    def test_the_same_route_with_a_decodable_image(self):
        """Negative control: a 500 above would otherwise just mean a broken route."""
        self.authenticate(None, None)
        document = self._request_document()
        buffer = io.BytesIO()
        Image.new("RGB", (400, 300), (10, 200, 10)).save(buffer, "PNG")

        response = self._upload(document, "fine.png", buffer.getvalue())

        self.assertEqual(response.status_code, 200)
        document.invalidate_recordset()
        self.assertEqual(document.thumbnail_status, "present")
        self.assertTrue(document.thumbnail)


@tagged("post_install", "-at_install")
class TestDocumentsThumbnailResolutionBound(TransactionCaseDocuments):
    """The preview decode is bounded by pixels, not only by bytes.

    `ir.attachment` normally downscales an uploaded image to 1920px before
    anything else sees it -- but `_documents_upload` builds its attachments
    `with_context(image_no_postprocess=True)`, so on the Documents upload route
    the full-size image reaches this compute. Pillow refuses only above twice
    its own `MAX_IMAGE_PIXELS`; below that it decodes, so a 410 KB PNG declaring
    12000x12000 used to decode in full and SUCCEED -- measured at +552 MB and
    0.80s for one request, against +0 MB and 0.04s once bounded. A request that
    succeeds is a better denial primitive than one that raises, because it can
    be repeated and logs nothing.
    """

    def _upload_shaped_attachment(self, name, side, mode="RGB"):
        buffer = io.BytesIO()
        Image.new(mode, (side, side)).save(buffer, "PNG")
        return (
            self.env["ir.attachment"]
            # the context the upload controller actually uses
            .with_context(no_document=True, image_no_postprocess=True)
            .create({"name": name, "raw": buffer.getvalue(), "mimetype": "image/png"})
        )

    def test_an_image_past_the_resolution_bound_is_stored_but_not_previewed(self):
        attachment = self._upload_shaped_attachment("huge.png", 8000)  # 64 Mpx
        self.assertLess(
            len(attachment.raw),
            1024 * 1024,
            "small on the wire, which is why a size limit does not catch it",
        )

        document = self.env["document.document"].create(
            {"name": "huge.png", "type": "binary", "attachment_id": attachment.id}
        )
        self.env.flush_all()

        self.assertEqual(document.thumbnail_status, "error")
        self.assertFalse(document.thumbnail)
        self.assertEqual(
            document.attachment_id.raw,
            attachment.raw,
            "the file itself is untouched; only its preview is skipped",
        )

    def test_an_ordinary_image_on_the_same_path_still_gets_a_thumbnail(self):
        """Negative control: the bound must not swallow normal photographs."""
        attachment = self._upload_shaped_attachment("normal.png", 2000)  # 4 Mpx

        document = self.env["document.document"].create(
            {"name": "normal.png", "type": "binary", "attachment_id": attachment.id}
        )
        self.env.flush_all()

        self.assertEqual(document.thumbnail_status, "present")
        self.assertTrue(document.thumbnail)
