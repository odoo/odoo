"""Tests for the S3 attachment storage addon.

These tests verify the config parameter logic and S3 key construction
without requiring a live AWS account — the ``boto3`` client is mocked
at the ``_s3_client`` seam.
"""

import hashlib
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from odoo.tests.common import TransactionCase


class TestS3KeyConstruction(TransactionCase):
    """Verify S3 key derivation from config parameters."""

    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()

    def _clear_s3_params(self):
        for key in (
            "ir_attachment.s3_bucket",
            "ir_attachment.s3_prefix",
            "ir_attachment.s3_region",
        ):
            self.ICP.set_param(key, "")

    def test_bucket_empty_uses_local_filestore(self):
        """With no bucket configured, _s3_bucket_name returns falsy."""
        self._clear_s3_params()
        self.assertFalse(self.env["ir.attachment"]._s3_bucket_name())

    def test_bucket_name_from_param(self):
        self.ICP.set_param("ir_attachment.s3_bucket", "my-odoo-bucket")
        self.assertEqual(
            self.env["ir.attachment"]._s3_bucket_name(),
            "my-odoo-bucket",
        )

    def test_prefix_gets_trailing_slash(self):
        self.ICP.set_param("ir_attachment.s3_prefix", "prod/filestore")
        self.assertEqual(
            self.env["ir.attachment"]._s3_prefix(),
            "prod/filestore/",
        )

    def test_prefix_already_has_slash(self):
        self.ICP.set_param("ir_attachment.s3_prefix", "prod/filestore/")
        self.assertEqual(
            self.env["ir.attachment"]._s3_prefix(),
            "prod/filestore/",
        )

    def test_prefix_empty(self):
        self._clear_s3_params()
        self.assertEqual(self.env["ir.attachment"]._s3_prefix(), "")

    def test_region_default(self):
        self._clear_s3_params()
        self.assertEqual(
            self.env["ir.attachment"]._s3_region(),
            "eu-west-1",
        )

    def test_region_from_param(self):
        self.ICP.set_param("ir_attachment.s3_region", "us-east-1")
        self.assertEqual(
            self.env["ir.attachment"]._s3_region(),
            "us-east-1",
        )

    def test_s3_key_no_prefix(self):
        """Without a prefix, key = fname directly."""
        self._clear_s3_params()
        self.assertEqual(
            self.env["ir.attachment"]._s3_key("ab/abcdef0123"),
            "ab/abcdef0123",
        )

    def test_s3_key_with_prefix(self):
        self.ICP.set_param("ir_attachment.s3_prefix", "prod/filestore")
        self.assertEqual(
            self.env["ir.attachment"]._s3_key("ab/abcdef0123"),
            "prod/filestore/ab/abcdef0123",
        )


class TestS3FileWrite(TransactionCase):
    """Verify _file_write logic with mocked S3 client."""

    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()
        self.ICP.set_param("ir_attachment.s3_bucket", "test-bucket")
        self.ICP.set_param("ir_attachment.s3_prefix", "")
        self.ICP.set_param("ir_attachment.s3_region", "eu-west-1")

    @patch("odoo.addons.s3_storage.models.ir_attachment.boto3")
    def test_file_write_returns_fname(self, mock_boto3):
        """_file_write should return the sha-based fname on success."""
        mock_client = MagicMock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_boto3.client.return_value = mock_client

        sha = hashlib.sha1(b"test-content").hexdigest()
        bin_value = b"test-content"

        fname = self.env["ir.attachment"]._file_write(bin_value, sha)

        self.assertEqual(fname, f"{sha[:2]}/{sha}")
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        self.assertEqual(call_kwargs["Bucket"], "test-bucket")
        self.assertEqual(call_kwargs["Body"], bin_value)
        self.assertTrue(call_kwargs["ServerSideEncryption"].startswith("aws:kms"))

    @patch("odoo.addons.s3_storage.models.ir_attachment.boto3")
    def test_file_write_deduplicates(self, mock_boto3):
        """When object exists with same size, skip upload."""
        mock_client = MagicMock()
        mock_client.head_object.return_value = {"ContentLength": 13}
        mock_boto3.client.return_value = mock_client

        sha = hashlib.sha1(b"test-content").hexdigest()
        fname = self.env["ir.attachment"]._file_write(b"test-content", sha)

        self.assertEqual(fname, f"{sha[:2]}/{sha}")
        mock_client.put_object.assert_not_called()


class TestS3FileDelete(TransactionCase):
    """Verify _file_delete logic with mocked S3 client."""

    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()
        self.ICP.set_param("ir_attachment.s3_bucket", "test-bucket")
        self.ICP.set_param("ir_attachment.s3_prefix", "")
        self.ICP.set_param("ir_attachment.s3_region", "eu-west-1")

    @patch("odoo.addons.s3_storage.models.ir_attachment.boto3")
    def test_file_delete_calls_s3(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        self.env["ir.attachment"]._file_delete("ab/abcdef0123")

        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="ab/abcdef0123",
        )


class TestS3FileRead(TransactionCase):
    """Verify _file_read logic with mocked S3 client."""

    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()
        self.ICP.set_param("ir_attachment.s3_bucket", "test-bucket")
        self.ICP.set_param("ir_attachment.s3_prefix", "files/")
        self.ICP.set_param("ir_attachment.s3_region", "eu-west-1")

    @patch("odoo.addons.s3_storage.models.ir_attachment.boto3")
    def test_file_read_returns_bytes(self, mock_boto3):
        mock_client = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"file-bytes"
        mock_client.get_object.return_value = {"Body": mock_body}
        mock_boto3.client.return_value = mock_client

        result = self.env["ir.attachment"]._file_read("ab/abcdef0123")

        self.assertEqual(result, b"file-bytes")
        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="files/ab/abcdef0123",
        )

    @patch("odoo.addons.s3_storage.models.ir_attachment.boto3")
    def test_file_read_missing_key_returns_empty(self, mock_boto3):
        mock_client = MagicMock()
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        mock_boto3.client.return_value = mock_client

        result = self.env["ir.attachment"]._file_read("ab/missing")
        self.assertEqual(result, b"")


class TestLocalFallback(TransactionCase):
    """When S3 bucket is not set, operations fall through to super."""

    def setUp(self):
        super().setUp()
        self.ICP = self.env["ir.config_parameter"].sudo()
        self.ICP.set_param("ir_attachment.s3_bucket", "")

    def test_file_write_uses_local(self):
        sha = hashlib.sha1(b"local-content").hexdigest()
        fname = self.env["ir.attachment"]._file_write(b"local-content", sha)
        self.assertEqual(fname, f"{sha[:2]}/{sha}")

    def test_file_read_uses_local(self):
        sha = hashlib.sha1(b"local-content").hexdigest()
        fname = self.env["ir.attachment"]._file_write(b"local-content", sha)
        result = self.env["ir.attachment"]._file_read(fname)
        self.assertEqual(result, b"local-content")

    def test_file_delete_uses_local(self):
        sha = hashlib.sha1(b"delete-me").hexdigest()
        fname = self.env["ir.attachment"]._file_write(b"delete-me", sha)
        self.env["ir.attachment"]._file_delete(fname)
