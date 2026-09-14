import base64
from types import SimpleNamespace
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import Stream
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import limited_field_access_token

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo

PNG_1x1_B64 = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC"


@tagged("post_install", "-at_install")
class TestIrBinaryNoRequest(TransactionCase):
    def test_get_stream_image_from_record_without_request(self):
        raw_png = base64.b64decode(PNG_1x1_B64)
        data_stream = Stream(
            type="data",
            data=raw_png,
            mimetype="image/png",
            etag="audit-irb-l1",
            size=len(raw_png),
        )
        ir_binary = self.env["ir.binary"]
        partner = self.env["res.partner"].create({"name": "Audit IRB-L1"})

        with (
            patch("odoo.addons.base.models.ir_binary.request", None),
            patch.object(
                type(ir_binary), "_get_stream_from_record", return_value=data_stream
            ),
        ):
            stream = ir_binary._get_stream_image_from_record(
                partner, "image_1920", width=64, height=64
            )

        self.assertEqual(stream.type, "data")
        self.assertTrue(stream.data)


@tagged("post_install", "-at_install")
class TestIrAttachmentNoRequest(TransactionCase):
    def test_to_http_stream_without_request(self):
        att = self.env["ir.attachment"].create({"name": "audit-new1", "raw": b"hello"})
        self.assertTrue(att.store_fname, "expected a filestore-backed attachment")
        with patch("odoo.addons.base.models.ir_attachment.request", None):
            stream = att._to_http_stream()
        self.assertEqual(stream.type, "path")
        self.assertEqual(stream.size, 5)


@tagged("post_install", "-at_install")
class TestIrBinaryImageMissing(TransactionCase):
    def test_missing_error_falls_back_to_placeholder(self):
        ir_binary = self.env["ir.binary"]
        partner = self.env["res.partner"].create({"name": "Audit IRB-C1"})

        def raise_missing(*args, **kwargs):
            raise MissingError("The related attachment does not exist.")

        with (
            patch("odoo.addons.base.models.ir_binary.request", None),
            patch.object(
                type(ir_binary), "_get_stream_from_record", side_effect=raise_missing
            ),
        ):
            stream = ir_binary._get_stream_image_from_record(partner, "image_1920")

        self.assertIsNotNone(stream)
        self.assertEqual(stream.type, "data")


@tagged("post_install", "-at_install")
class TestIrBinaryFindRecordAccess(TransactionCaseWithUserDemo):
    def test_valid_field_token_grants_sudo(self):
        partner = self.env["res.partner"].create({"name": "Audit IRB-T1 token"})
        token = limited_field_access_token(partner, "image_1920", scope="binary")
        record = (
            self.env["ir.binary"]
            .with_user(self.user_demo)
            ._get_record(
                res_model="res.partner",
                res_id=partner.id,
                access_token=token,
                field_name="image_1920",
            )
        )
        self.assertTrue(record.env.su, "a valid field token must return a sudo record")

    def test_mismatched_token_does_not_grant_sudo(self):
        partner = self.env["res.partner"].create({"name": "Audit IRB-T1 bad token"})
        record = (
            self.env["ir.binary"]
            .with_user(self.user_demo)
            ._get_record(
                res_model="res.partner",
                res_id=partner.id,
                access_token="not-a-valid-tokeno0",
                field_name="image_1920",
            )
        )
        self.assertFalse(
            record.env.su, "a mismatched token must not bypass to a sudo record"
        )

    def test_no_read_access_falls_through_and_raises(self):
        parameter = self.env["ir.config_parameter"].create(
            {"key": "test.ir_binary.no_read", "value": "x"}
        )
        with self.assertRaises(AccessError):
            self.env["ir.binary"].with_user(self.user_demo)._get_record(
                res_model="ir.config_parameter", res_id=parameter.id
            )


@tagged("post_install", "-at_install")
class TestIrBinaryImageBranches(TransactionCase):
    @property
    def _binary(self):
        return self.env["ir.binary"]

    def _partner(self, name):
        return self.env["res.partner"].create({"name": name})

    def _png_stream(self, etag="audit-irb-c2"):
        raw_png = base64.b64decode(PNG_1x1_B64)
        return Stream(
            type="data",
            data=raw_png,
            mimetype="image/png",
            etag=etag,
            size=len(raw_png),
        )

    def test_swallowed_error_is_logged_at_debug(self):
        partner = self._partner("Audit IRB-C2 log")

        def raise_user_error(*args, **kwargs):
            raise UserError("Record has no field 'image_1920_typo'.")

        with (
            patch("odoo.addons.base.models.ir_binary.request", None),
            patch.object(
                type(self._binary),
                "_get_stream_from_record",
                side_effect=raise_user_error,
            ),
            self.assertLogs("odoo.addons.base.models.ir_binary", level="DEBUG") as cm,
        ):
            stream = self._binary._get_stream_image_from_record(partner, "image_1920")
        self.assertEqual(stream.type, "data")
        joined = "\n".join(cm.output)
        self.assertIn("image placeholder", joined)
        self.assertIn("image_1920_typo", joined)
        self.assertIn("res.partner", joined)

    def test_explicit_download_re_raises(self):
        partner = self._partner("Audit IRB-C2 download")
        fake_request = SimpleNamespace(params={"download": "1"})

        def raise_missing(*args, **kwargs):
            raise MissingError("The related attachment does not exist.")

        with (
            patch("odoo.addons.base.models.ir_binary.request", fake_request),
            patch.object(
                type(self._binary), "_get_stream_from_record", side_effect=raise_missing
            ),
        ):
            with self.assertRaises(MissingError):
                self._binary._get_stream_image_from_record(partner, "image_1920")

    def test_empty_stream_falls_back_to_placeholder(self):
        partner = self._partner("Audit IRB-C2 empty")
        empty = Stream(type="data", data=b"", mimetype="image/png", size=0)
        with (
            patch("odoo.addons.base.models.ir_binary.request", None),
            patch.object(
                type(self._binary), "_get_stream_from_record", return_value=empty
            ),
        ):
            stream = self._binary._get_stream_image_from_record(partner, "image_1920")
        self.assertEqual(stream.type, "data")
        self.assertTrue(stream.size, "placeholder must carry actual bytes")

    def test_etag_augmented_with_processing_params(self):
        partner = self._partner("Audit IRB-C2 etag")
        with (
            patch("odoo.addons.base.models.ir_binary.request", None),
            patch.object(
                type(self._binary),
                "_get_stream_from_record",
                return_value=self._png_stream(etag="base-etag"),
            ),
        ):
            stream = self._binary._get_stream_image_from_record(
                partner, "image_1920", width=64, height=32, crop=True, quality=80
            )
        self.assertEqual(stream.etag, "base-etag-64x32-crop=True-quality=80")
        self.assertEqual(stream.type, "data")
        self.assertTrue(stream.data)


@tagged("post_install", "-at_install")
class TestIrBinaryFilenameField(TransactionCaseWithUserDemo):
    def setUp(self):
        super().setUp()
        self.attachment = self.env["ir.attachment"].create(
            {"name": "pub.txt", "raw": b"public bytes", "public": True}
        )
        model = self.env["ir.model"]._get("ir.attachment")
        self.env["ir.model.fields"].create(
            {
                "name": "x_secret_name",
                "model_id": model.id,
                "ttype": "char",
                "field_description": "Secret name",
                "groups": [Command.link(self.env.ref("base.group_system").id)],
            }
        )
        self.attachment.write({"x_secret_name": "SECRET.txt"})

    def _download_name(self, filename_field):
        record = self.attachment.with_user(self.user_demo).sudo()
        stream = (
            self.env["ir.binary"]
            .with_user(self.user_demo)
            ._get_stream_from_record(record, "raw", filename_field=filename_field)
        )
        return stream.download_name

    def test_a_group_restricted_char_whose_name_contains_name_is_not_disclosed(self):
        self.assertEqual(self._download_name("x_secret_name"), "pub.txt")

    def test_a_non_char_filename_field_falls_back_to_the_default_name(self):
        for field_name in ("res_id", "create_date", "public"):
            with self.subTest(field_name=field_name):
                self.assertEqual(self._download_name(field_name), "pub.txt")

    def test_the_name_field_itself_still_names_the_download(self):
        self.assertEqual(self._download_name("name"), "pub.txt")
