from unittest.mock import MagicMock, patch
from urllib.parse import quote

from botocore.exceptions import ClientError

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, tagged

from .. import uninstall_hook
from ..tools import drive_import, s3

CLIENT_FACTORY = "odoo.addons.cloud_storage_s3.tools.s3.boto3.client"


class TestCloudStorageS3Common(TransactionCase):
    def setUp(self):
        super().setUp()
        self.bucket_name = "test-odoo-bucket"
        self.region = "us-east-2"
        self.access_key_id = "AKIAIOSFODNN7EXAMPLE"
        self.secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

        icp = self.env["ir.config_parameter"]
        icp.set_param("cloud_storage_s3_enabled", "True")
        icp.set_param("cloud_storage_provider", "s3")
        icp.set_param(s3.PARAM_BUCKET, self.bucket_name)
        icp.set_param(s3.PARAM_REGION, self.region)
        s3.store_keys(self.env, self.access_key_id, self.secret_access_key)

        self.mock_s3_client = MagicMock()
        self.mock_s3_client.generate_presigned_url.return_value = (
            "https://presigned.example.com/test"
        )
        self.mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )

        self._boto3_patcher = patch(CLIENT_FACTORY, return_value=self.mock_s3_client)
        self._boto3_patcher.start()

    def tearDown(self):
        self._boto3_patcher.stop()
        s3.clear_cache()
        super().tearDown()


class TestCloudStorageS3(TestCloudStorageS3Common):
    def test_generate_cloud_storage_url(self):
        attachment = self.env["ir.attachment"].create(
            [{"name": "test.txt", "mimetype": "text/plain", "datas": b""}]
        )
        attachment._post_add_create(cloud_storage=True)
        self.assertTrue(
            attachment.url.startswith(
                f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/"
            ),
            "URL should use the S3 virtual-hosted style",
        )

    def test_generate_url_with_special_characters(self):
        file_name = "reporte año 2026 (final).pdf"
        attachment = self.env["ir.attachment"].create(
            [{"name": file_name, "mimetype": "application/pdf", "datas": b""}]
        )
        attachment._post_add_create(cloud_storage=True)
        self.assertIn(
            quote(file_name),
            attachment.url,
            "Special characters in filename should be URL-encoded",
        )

    def test_generate_presigned_download_info(self):
        attachment = self.env["ir.attachment"].create(
            [{"name": "test.txt", "mimetype": "text/plain", "datas": b""}]
        )
        attachment._post_add_create(cloud_storage=True)
        info = attachment._generate_cloud_storage_download_info()
        self.assertIn("url", info)
        self.assertIn("time_to_expiry", info)
        self.mock_s3_client.generate_presigned_url.assert_called()

    def test_generate_presigned_upload_info(self):
        attachment = self.env["ir.attachment"].create(
            [{"name": "test.txt", "mimetype": "text/plain", "datas": b""}]
        )
        attachment._post_add_create(cloud_storage=True)
        info = attachment._generate_cloud_storage_upload_info()
        self.assertEqual(info["method"], "PUT")
        self.assertEqual(info["response_status"], 200)

    def test_blob_name_structure(self):
        attachment = self.env["ir.attachment"].create(
            [
                {
                    "name": "document.pdf",
                    "mimetype": "application/pdf",
                    "datas": b"",
                    "res_model": "res.partner",
                    "res_id": 1,
                }
            ]
        )
        attachment._post_add_create(cloud_storage=True)
        self.assertIn("res_partner/1/", attachment.url)

    def test_s3_url_validation(self):
        attachment = self.env["ir.attachment"].create(
            [
                {
                    "name": "test.txt",
                    "mimetype": "text/plain",
                    "type": "cloud_storage",
                    "url": f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/res_partner/1/42_abc12345_test.txt",
                }
            ]
        )
        info = attachment._get_s3_info()
        self.assertEqual(info["bucket_name"], self.bucket_name)
        self.assertEqual(info["region"], self.region)
        self.assertEqual(info["blob_name"], "res_partner/1/42_abc12345_test.txt")

    def test_s3_url_validation_invalid(self):
        attachment = self.env["ir.attachment"].create(
            [
                {
                    "name": "test.txt",
                    "mimetype": "text/plain",
                    "type": "cloud_storage",
                    "url": "https://storage.googleapis.com/bucket/blob",
                }
            ]
        )
        with self.assertRaises(ValidationError):
            attachment._get_s3_info()

    def test_unlink_deletes_s3_blobs_batch(self):
        attachments = self.env["ir.attachment"]
        for i in range(3):
            attachments |= self.env["ir.attachment"].create(
                [
                    {
                        "name": f"file_{i}.txt",
                        "mimetype": "text/plain",
                        "type": "cloud_storage",
                        "url": f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/test/{i}_abc_file_{i}.txt",
                    }
                ]
            )
        attachments.unlink()
        self.mock_s3_client.delete_objects.assert_called_once()
        call_args = self.mock_s3_client.delete_objects.call_args
        self.assertEqual(call_args.kwargs["Bucket"], self.bucket_name)
        self.assertEqual(len(call_args.kwargs["Delete"]["Objects"]), 3)

    def test_unlink_non_s3_attachments_ignored(self):
        attachment = self.env["ir.attachment"].create(
            [
                {
                    "name": "local.txt",
                    "mimetype": "text/plain",
                    "datas": b"",
                }
            ]
        )
        attachment.unlink()
        self.mock_s3_client.delete_objects.assert_not_called()

    def test_client_cache_invalidation(self):
        with patch(CLIENT_FACTORY, side_effect=lambda *a, **kw: MagicMock()):
            s3.clear_cache()
            client1 = s3.get_client(self.env)
            client2 = s3.get_client(self.env)
            self.assertIs(client1, client2)

            s3.store_keys(self.env, "NEWKEY", self.secret_access_key)
            client3 = s3.get_client(self.env)
            self.assertIsNot(client1, client3)

    def test_keys_live_in_the_vault_only(self):
        credential = s3.get_credential(self.env)
        self.assertEqual(credential.storage_method, "json")
        self.assertEqual(
            credential.get_credential_dict(),
            {
                "access_key_id": self.access_key_id,
                "secret_access_key": self.secret_access_key,
            },
        )
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT count(*) FROM ir_config_parameter WHERE value LIKE %s",
            (f"%{self.secret_access_key}%",),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)

    def test_settings_store_keys_and_clear_the_wizard_row(self):
        settings = self.env["res.config.settings"].create(
            {
                "cloud_storage_s3_access_key_id": "AKIANEWKEY",
                "cloud_storage_s3_secret_access_key": "newsecret",
            }
        )
        with patch.object(
            type(settings), "_setup_cloud_storage_provider", return_value=None
        ):
            settings.set_values()
        self.assertEqual(s3.get_keys(self.env)["access_key_id"], "AKIANEWKEY")
        self.assertFalse(settings.cloud_storage_s3_access_key_id)
        self.assertFalse(settings.cloud_storage_s3_secret_access_key)
        self.assertTrue(settings.cloud_storage_s3_keys_set)
        self.assertTrue(
            self.env["res.config.settings"].get_values()["cloud_storage_s3_keys_set"]
        )

    def test_settings_refuse_half_a_key_pair(self):
        settings = self.env["res.config.settings"].create(
            {"cloud_storage_s3_access_key_id": "AKIANEWKEY"}
        )
        with self.assertRaises(UserError):
            settings.set_values()

    def test_configuration_needs_the_vault_keys(self):
        settings = self.env["res.config.settings"].new({})
        self.assertTrue(settings._get_cloud_storage_configuration())
        s3.get_credential(self.env).active = False
        s3.clear_cache()
        self.assertFalse(settings._get_cloud_storage_configuration())

    def test_is_s3_provider(self):
        attachment = self.env["ir.attachment"].new()
        self.assertTrue(attachment._is_s3_provider())

        self.env["ir.config_parameter"].set_param("cloud_storage_provider", "google")
        self.assertFalse(attachment._is_s3_provider())

    def test_uninstall_fail(self):
        with self.assertRaises(UserError):
            attachment = self.env["ir.attachment"].create(
                [{"name": "test.txt", "mimetype": "text/plain", "datas": b""}]
            )
            attachment._post_add_create(cloud_storage=True)
            attachment.flush_recordset()
            uninstall_hook(self.env)

    def test_uninstall_success(self):
        uninstall_hook(self.env)
        icp = self.env["ir.config_parameter"]
        self.assertFalse(icp.get_param("cloud_storage_provider"))
        self.assertFalse(icp.get_param(s3.PARAM_BUCKET))
        self.assertFalse(icp.get_param(s3.PARAM_REGION))
        self.assertFalse(s3.get_credential(self.env))


class TestCloudStorageS3Hybrid(TestCloudStorageS3Common):
    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].set_param(
            "cloud_storage_s3_storage_mode", "hybrid"
        )

    def _make_attachment(self, **vals):
        defaults = {
            "name": "doc.txt",
            "raw": b"hello world",
            "res_model": "res.partner",
            "res_id": 1,
        }
        defaults.update(vals)
        return self.env["ir.attachment"].create([defaults])

    def test_create_flags_business_attachment_pending(self):
        attachment = self._make_attachment()
        self.assertEqual(attachment.type, "binary")
        self.assertTrue(attachment.s3_mirror_pending)

    def test_create_does_not_upload_in_the_request_transaction(self):
        attachment = self._make_attachment()
        self.assertTrue(attachment.s3_mirror_pending)
        self.assertEqual(
            len(self.env.cr.postcommit),
            0,
            "the mirror must not be queued on the request cursor: running it "
            "there uploads to S3 while the main transaction sits idle",
        )
        self.env.cr.postcommit.run()
        self.mock_s3_client.put_object.assert_not_called()
        self.assertTrue(attachment.s3_mirror_pending)

    def test_create_skips_system_assets(self):
        attachment = self.env["ir.attachment"].create(
            [{"name": "bundle.js", "raw": b"console.log(1)"}]
        )
        self.assertFalse(attachment.s3_mirror_pending)

    def test_post_add_create_keeps_local_in_hybrid(self):
        attachment = self._make_attachment()
        attachment._post_add_create(cloud_storage=True)
        self.assertEqual(attachment.type, "binary")
        self.assertFalse(attachment.url)

    def test_mirror_uploads_and_clears_pending(self):
        attachment = self._make_attachment()
        attachment._s3_mirror_to_cloud()
        self.mock_s3_client.put_object.assert_called_once()
        call = self.mock_s3_client.put_object.call_args
        self.assertEqual(call.kwargs["Bucket"], self.bucket_name)
        self.assertEqual(call.kwargs["Body"], b"hello world")
        self.assertFalse(attachment.s3_mirror_pending)
        self.assertTrue(attachment.s3_blob_name)

    def test_mirror_failure_keeps_pending(self):
        self.mock_s3_client.put_object.side_effect = Exception("network down")
        attachment = self._make_attachment()
        attachment._s3_mirror_to_cloud()
        self.assertTrue(attachment.s3_mirror_pending)
        self.assertFalse(attachment.s3_blob_name)

    def test_cron_mirrors_pending(self):
        attachment = self._make_attachment()
        self.env["ir.attachment"]._cron_mirror_pending_to_s3()
        self.mock_s3_client.put_object.assert_called()
        self.assertFalse(attachment.s3_mirror_pending)

    def test_unlink_deletes_hybrid_mirror(self):
        attachment = self._make_attachment()
        attachment._s3_mirror_to_cloud()
        blob_name = attachment.s3_blob_name
        attachment.unlink()
        self.mock_s3_client.delete_objects.assert_called_once()
        call = self.mock_s3_client.delete_objects.call_args
        self.assertEqual(call.kwargs["Bucket"], self.bucket_name)
        self.assertEqual(call.kwargs["Delete"]["Objects"], [{"Key": blob_name}])

    def test_write_flags_late_res_model(self):
        attachment = self.env["ir.attachment"].create(
            [{"name": "late.pdf", "raw": b"pdf-bytes"}]
        )
        self.assertFalse(attachment.s3_mirror_pending)
        attachment.write({"res_model": "document.document", "res_id": 99})
        self.assertTrue(attachment.s3_mirror_pending)

    def test_blob_name_mirrors_filestore(self):
        attachment = self._make_attachment()
        attachment._s3_mirror_to_cloud()
        self.assertEqual(attachment.s3_blob_name, attachment.store_fname)

    def test_unlink_keeps_shared_blob(self):
        a1 = self._make_attachment(name="a.txt")
        a2 = self._make_attachment(name="b.txt")
        a1._s3_mirror_to_cloud()
        a2._s3_mirror_to_cloud()
        self.assertEqual(a1.s3_blob_name, a2.s3_blob_name)
        a1.unlink()
        self.mock_s3_client.delete_objects.assert_not_called()
        a2.unlink()
        self.mock_s3_client.delete_objects.assert_called_once()

    def test_mirror_skips_existing_object(self):
        self.mock_s3_client.head_object.side_effect = None
        self.mock_s3_client.head_object.return_value = {"ContentLength": 11}
        attachment = self._make_attachment()
        attachment._s3_mirror_to_cloud()
        self.mock_s3_client.put_object.assert_not_called()
        self.assertFalse(attachment.s3_mirror_pending)
        self.assertTrue(attachment.s3_blob_name)

    def test_backfill_mirrors_existing(self):
        attachment = self._make_attachment()
        attachment.s3_mirror_pending = False
        self.assertFalse(attachment.s3_blob_name)
        self.env["ir.attachment"]._s3_backfill_to_s3(
            batch_size=1000, commit_each_batch=False
        )
        self.assertTrue(attachment.s3_blob_name)
        self.assertFalse(attachment.s3_mirror_pending)

    def test_backfill_includes_binary_field_attachments(self):
        attachment = self._make_attachment(res_field="image_128")
        attachment.s3_mirror_pending = False
        self.assertFalse(attachment.s3_blob_name)
        self.env["ir.attachment"]._s3_backfill_to_s3(
            batch_size=1000, commit_each_batch=False
        )
        self.assertEqual(attachment.s3_blob_name, attachment.store_fname)
        self.assertFalse(attachment.s3_mirror_pending)

    def test_cron_retries_binary_field_attachments(self):
        attachment = self._make_attachment(res_field="image_128")
        self.assertTrue(attachment.s3_mirror_pending)
        self.env["ir.attachment"]._cron_mirror_pending_to_s3()
        self.assertFalse(attachment.s3_mirror_pending)
        self.assertEqual(attachment.s3_blob_name, attachment.store_fname)

    def test_unlink_keeps_blob_shared_with_binary_field_attachment(self):
        doc = self._make_attachment(name="doc.txt")
        field_att = self._make_attachment(name="field.bin", res_field="image_128")
        doc._s3_mirror_to_cloud()
        field_att._s3_mirror_to_cloud()
        self.assertEqual(doc.s3_blob_name, field_att.s3_blob_name)
        doc.unlink()
        self.mock_s3_client.delete_objects.assert_not_called()

    def test_disabled_environment_skips_s3(self):
        self.env["ir.config_parameter"].set_param("cloud_storage_s3_enabled", "False")
        attachment = self._make_attachment()
        self.assertFalse(attachment.s3_mirror_pending)
        self.env["ir.attachment"]._cron_mirror_pending_to_s3()
        self.env["ir.attachment"]._s3_backfill_to_s3()
        self.mock_s3_client.put_object.assert_not_called()

    def test_unlink_disabled_skips_s3_delete(self):
        attachment = self._make_attachment()
        attachment._s3_mirror_to_cloud()
        self.assertTrue(attachment.s3_blob_name)
        self.env["ir.config_parameter"].set_param("cloud_storage_s3_enabled", "False")
        attachment.unlink()
        self.mock_s3_client.delete_objects.assert_not_called()

    def test_config_available_when_disabled(self):
        self.env["ir.config_parameter"].set_param("cloud_storage_s3_enabled", "False")
        settings = self.env["res.config.settings"].new({})
        self.assertTrue(settings._get_cloud_storage_configuration())


def _page(*objects):
    return [{"Contents": [{"Key": key, "Size": size} for key, size in objects]}]


@tagged("post_install", "-at_install")
class TestDriveImport(TestCloudStorageS3Common):
    def setUp(self):
        super().setUp()
        if "document.document" not in self.env:
            self.skipTest("document is not installed")
        self.user = self.env["res.users"].create(
            {"name": "Drive Viewer", "login": "drive_viewer"}
        )
        self.admin = self.env["res.users"].create(
            {"name": "Drive Admin", "login": "drive_admin"}
        )
        paginator = MagicMock()
        paginator.paginate.return_value = _page(
            ("06 Partners/", 0),
            ("06 Partners/ACME/contract.pdf", 1234),
            ("06 Partners/ACME/logo.png", 99),
            ("Empty Folder/", 0),
            ("readme.txt", 7),
        )
        self.mock_s3_client.get_paginator.return_value = paginator

    def _import(self, grants=()):
        return drive_import.import_bucket(
            self.env,
            self.mock_s3_client,
            "drive-bucket",
            self.region,
            root_name="Cloud",
            grants=grants,
        )

    def test_objects_become_a_folder_tree_over_the_existing_keys(self):
        result = self._import()
        root = self.env["document.document"].browse(result["root_id"])
        self.assertEqual(root.type, "folder")
        self.assertTrue(root._is_company_root_folder())
        self.assertEqual(result["folders"], 3)
        self.assertEqual(result["files"], 3)
        contract = self.env["document.document"].search([("name", "=", "contract.pdf")])
        self.assertEqual(contract.folder_id.name, "ACME")
        self.assertEqual(contract.folder_id.folder_id.name, "06 Partners")
        self.assertEqual(contract.folder_id.folder_id.folder_id, root)
        attachment = contract.attachment_id
        self.assertEqual(attachment.type, "cloud_storage")
        self.assertEqual(
            attachment.url,
            f"https://drive-bucket.s3.{self.region}.amazonaws.com/"
            + quote("06 Partners/ACME/contract.pdf"),
        )
        self.assertEqual(attachment.mimetype, "application/pdf")
        self.assertEqual(attachment.file_size, 1234)
        self.assertEqual(attachment.res_model, "document.document")
        self.assertEqual(attachment.res_id, contract.id)
        self.assertEqual(
            contract.attachment_id._get_s3_info()["blob_name"],
            "06 Partners/ACME/contract.pdf",
        )
        self.mock_s3_client.put_object.assert_not_called()
        self.mock_s3_client.copy_object.assert_not_called()

    def test_grants_map_onto_documents_access(self):
        result = self._import(
            grants=[
                {
                    "path": "06 Partners",
                    "user_id": self.user.id,
                    "access_level": "read",
                },
                {
                    "path": "06 Partners/ACME",
                    "user_id": self.admin.id,
                    "access_level": "admin",
                },
                {
                    "path": "readme.txt",
                    "user_id": self.user.id,
                    "access_level": "upload",
                },
                {"path": "missing", "user_id": self.user.id, "access_level": "read"},
            ]
        )
        self.assertEqual(result["grants"], 3)
        self.assertEqual([g["path"] for g in result["skipped_grants"]], ["missing"])
        documents = self.env["document.document"]
        partners = documents.search([("name", "=", "06 Partners")])
        self.assertEqual(partners.access_ids.partner_id, self.user.partner_id)
        self.assertEqual(partners.access_ids.role, "view")
        acme = documents.search([("name", "=", "ACME")])
        self.assertEqual(acme.owner_id, self.admin)
        roles = {access.partner_id: access.role for access in acme.access_ids}
        self.assertEqual(roles[self.admin.partner_id], "edit")
        self.assertEqual(roles[self.user.partner_id], "view")
        readme = documents.search([("name", "=", "readme.txt")])
        self.assertEqual(readme.access_ids.role, "edit")
        self.assertEqual(partners.with_user(self.user).user_permission, "view")
        self.assertEqual(acme.with_user(self.user).user_permission, "view")
        self.assertEqual(readme.with_user(self.user).user_permission, "edit")

    def test_cloud_images_thumbnails_are_client_generated(self):
        self._import()
        logo = self.env["document.document"].search([("name", "=", "logo.png")])
        self.assertEqual(logo.thumbnail_status, "client_generated")


@tagged("post_install", "-at_install")
class TestDocumentsDirectUpload(HttpCase):
    def setUp(self):
        super().setUp()
        if "document.document" not in self.env:
            self.skipTest("document is not installed")
        icp = self.env["ir.config_parameter"]
        icp.set_param("cloud_storage_s3_enabled", "True")
        icp.set_param("cloud_storage_provider", "s3")
        icp.set_param(s3.PARAM_BUCKET, "test-odoo-bucket")
        icp.set_param(s3.PARAM_REGION, "us-east-2")
        s3.store_keys(self.env, "AKIAIOSFODNN7EXAMPLE", "secret")
        client = MagicMock()
        client.generate_presigned_url.return_value = "https://presigned.example.com/put"
        self._boto3_patcher = patch(CLIENT_FACTORY, return_value=client)
        self._boto3_patcher.start()
        self.uploader = self.env["res.users"].create(
            {
                "name": "Uploader",
                "login": "uploader",
                "password": "uploader_pwd",
                "group_ids": [
                    (6, 0, [self.env.ref("document.group_documents_user").id])
                ],
            }
        )

    def tearDown(self):
        self._boto3_patcher.stop()
        s3.clear_cache()
        super().tearDown()

    def test_upload_route_signs_a_direct_upload(self):
        self.authenticate("uploader", "uploader_pwd")
        response = self.url_open(
            "/documents/upload/",
            data={
                "csrf_token": http.Request.csrf_token(self),
                "user_folder_id": "MY",
                "cloud_storage": "1",
                "file_size": "4096",
            },
            files={"ufile": ("big.bin", b"", "application/octet-stream")},
        )
        response.raise_for_status()
        payload = response.json()
        document = self.env["document.document"].browse(payload["document_ids"])
        self.assertEqual(payload["upload_info"]["method"], "PUT")
        self.assertEqual(
            payload["upload_info"]["url"], "https://presigned.example.com/put"
        )
        attachment = document.attachment_id
        self.assertEqual(attachment.type, "cloud_storage")
        self.assertEqual(attachment.file_size, 4096)
        self.assertEqual(document.file_size, 4096)
        self.assertIn("document_document/", attachment.url)
        self.assertEqual(attachment.res_id, document.id)
        self.assertNotIn(
            "document.document",
            self.env["ir.attachment"]._get_cloud_storage_unsupported_models(),
        )


@tagged("post_install", "-at_install")
class TestS3CredentialSlots(TransactionCase):
    def test_the_category_declares_both_iam_keys(self):
        category = self.env.ref(s3.CREDENTIAL_CATEGORY_XMLID)

        self.assertEqual(
            set(category.field_ids.mapped("code")),
            {"access_key_id", "secret_access_key"},
        )

    def test_a_credential_missing_the_secret_key_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env["credential.credential"].create(
                {
                    "name": "S3 without its secret",
                    "category_id": self.env.ref(s3.CREDENTIAL_CATEGORY_XMLID).id,
                    "credential_data": '{"access_key_id": "AKIA"}',
                }
            )
