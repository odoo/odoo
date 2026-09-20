import uuid
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCloudStorage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attachment = cls.env["ir.attachment"].create(
            {"name": "cloud.txt", "raw": b"payload"}
        )

    def test_generate_url_is_abstract(self):
        """The provider-agnostic base leaves blob URL generation unimplemented."""
        with self.assertRaises(NotImplementedError):
            self.attachment._generate_cloud_storage_url()

    def test_generate_download_info_is_abstract(self):
        """The base module has no download-info implementation."""
        with self.assertRaises(NotImplementedError):
            self.attachment._generate_cloud_storage_download_info()

    def test_generate_upload_info_is_abstract(self):
        """The base module has no upload-info implementation."""
        with self.assertRaises(NotImplementedError):
            self.attachment._generate_cloud_storage_upload_info()

    def test_post_add_create_without_provider_raises(self):
        """Flagging an attachment as cloud storage needs an enabled provider."""
        self.env["ir.config_parameter"].sudo().set_param("cloud_storage_provider", "")
        with self.assertRaises(UserError):
            self.attachment._post_add_create(cloud_storage=True)

    def test_blob_name_is_scoped_to_attachment(self):
        """The blob name embeds the attachment id, a uuid4, and the file name."""
        blob_name = self.attachment._generate_cloud_storage_blob_name()
        prefix, token, name = blob_name.split("/")
        self.assertEqual(prefix, str(self.attachment.id))
        self.assertEqual(name, self.attachment.name)
        # a malformed token would raise ValueError and fail the test
        self.assertEqual(str(uuid.UUID(token)), token)

    def test_get_values_reports_min_file_size_in_mb(self):
        """Settings expose the byte threshold converted to megabytes."""
        self.env["ir.config_parameter"].sudo().set_param(
            "cloud_storage_min_file_size", "30000000"
        )
        values = self.env["res.config.settings"].get_values()
        self.assertEqual(values["cloud_storage_min_file_size_mb"], 30)

    def test_documents_are_not_excluded_from_the_cloud(self):
        """Only main-attachment models keep their bytes on the server."""
        unsupported = self.env["ir.attachment"]._get_cloud_storage_unsupported_models()
        self.assertNotIn("document.document", unsupported)

    def test_fetch_content_downloads_the_blob_a_provider_holds(self):
        """A cloud attachment has no local bytes: the fetch goes and gets them."""
        remote = self.env["ir.attachment"].create({"name": "remote.pdf"})
        remote.type = "cloud_storage"
        self.assertFalse(remote.raw, "the blob is not in this database")
        self.assertEqual(remote._get_content_prefix(), b"", "nothing is stored here")

        calls = []

        class Response:
            content = b"%PDF-1.7 fetched"

            def raise_for_status(self):
                return None

        def fake_get(url, timeout=None, headers=None):
            calls.append((url, headers))
            return Response()

        with (
            patch.object(
                type(remote),
                "_generate_cloud_storage_download_info",
                lambda self: {"url": "https://bucket/blob", "time_to_expiry": 300},
            ),
            patch("odoo.addons.cloud_storage.models.ir_attachment.requests.get", fake_get),
        ):
            self.assertEqual(remote._fetch_content(), b"%PDF-1.7 fetched")
            remote._fetch_content(64)

        self.assertEqual([call[0] for call in calls], ["https://bucket/blob"] * 2)
        self.assertEqual(calls[0][1], {}, "a whole blob asks for no range")
        self.assertEqual(
            calls[1][1],
            {"Range": "bytes=0-63"},
            "a sized read asks the provider for a prefix instead of the file",
        )

    def test_fetch_content_of_a_local_blob_stays_local(self):
        """An attachment this database stores is never fetched over the network."""

        def explode(*args, **kwargs):
            raise AssertionError("a local blob must not reach the provider")

        with patch(
            "odoo.addons.cloud_storage.models.ir_attachment.requests.get", explode
        ):
            self.assertEqual(self.attachment._fetch_content(), b"payload")
            self.assertEqual(self.attachment._fetch_content(3), b"pay")
