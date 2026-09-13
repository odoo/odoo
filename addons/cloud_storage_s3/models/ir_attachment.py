import logging
import re
import uuid
from collections import defaultdict
from itertools import batched
from urllib.parse import unquote

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..tools import s3

_logger = logging.getLogger(__name__)

S3_URL_PATTERN = re.compile(
    r"^https://(?P<bucket_name>[\w\-.]+)\.s3\.(?P<region>[\w\-.]+)\.amazonaws\.com/(?P<blob_name>[^?]+)$"
)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    s3_blob_name = fields.Char(
        copy=False,
        help="Object key of the copy mirrored to S3 in hybrid mode.",
    )
    s3_mirror_pending = fields.Boolean(
        default=False,
        index=True,
        copy=False,
        help="Set when this attachment still needs to be mirrored to S3 "
        "(hybrid mode). Cleared once the upload succeeds.",
    )

    def _s3_is_enabled(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param("cloud_storage_s3_enabled")
            == "True"
        )

    def _is_s3_provider(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param("cloud_storage_provider")
            == "s3"
        )

    def _is_s3_hybrid(self):
        if not self._s3_is_enabled():
            return False
        icp = self.env["ir.config_parameter"].sudo()
        return (
            icp.get_param("cloud_storage_provider") == "s3"
            and icp.get_param("cloud_storage_s3_storage_mode") == "hybrid"
        )

    def _filter_s3_mirrorable(self):
        return self.filtered(
            lambda a: (
                a.type == "binary" and (a.store_fname or a.db_datas) and a.res_model
            )
        )

    def _s3_queue_mirror(self):
        # Only flag the rows: the upload is left to
        # ``_cron_mirror_pending_to_s3``. Uploading from a postcommit callback
        # runs it in the request thread, which keeps the main transaction
        # idle-in-transaction for as long as S3 takes to answer.
        to_mirror = self._filter_s3_mirrorable()
        if to_mirror:
            to_mirror.s3_mirror_pending = True

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        if attachments and attachments._is_s3_hybrid():
            attachments._s3_queue_mirror()
        return attachments

    _S3_MIRROR_TRIGGER_FIELDS = frozenset(
        {"res_model", "res_id", "raw", "datas", "db_datas", "store_fname", "type"}
    )

    def write(self, vals):
        res = super().write(vals)
        if self._S3_MIRROR_TRIGGER_FIELDS & vals.keys() and self._is_s3_hybrid():
            self.filtered(
                lambda a: not a.s3_blob_name and not a.s3_mirror_pending
            )._s3_queue_mirror()
        return res

    def _post_add_create(self, **kwargs):
        if kwargs.get("cloud_storage") and self._is_s3_hybrid():
            kwargs = {k: v for k, v in kwargs.items() if k != "cloud_storage"}
        return super()._post_add_create(**kwargs)

    def _s3_hybrid_blob_name(self):
        self.check_singleton()
        return self.store_fname or self._generate_cloud_storage_blob_name()

    def _s3_bucket_name(self):
        return self.env["ir.config_parameter"].sudo().get_param(s3.PARAM_BUCKET)

    def _s3_mirror_to_cloud(self):
        if not self or not self._s3_is_enabled():
            return
        bucket = self._s3_bucket_name()
        if not bucket:
            _logger.error("S3 mirror skipped: no bucket configured.")
            return
        client = s3.get_client(self.env)
        for attach in self:
            try:
                blob_name = attach.s3_blob_name or attach._s3_hybrid_blob_name()
                if s3.object_exists(client, bucket, blob_name):
                    attach.write(
                        {"s3_blob_name": blob_name, "s3_mirror_pending": False}
                    )
                    continue
                data = attach.raw
                if not data:
                    attach.write({"s3_mirror_pending": False})
                    continue
                client.put_object(Bucket=bucket, Key=blob_name, Body=data)
                attach.write({"s3_blob_name": blob_name, "s3_mirror_pending": False})
            except Exception:
                _logger.warning(
                    "Failed to mirror attachment %s to S3; will retry on the "
                    "next cron run.",
                    attach.id,
                    exc_info=True,
                )

    @api.model
    def _s3_backfill_to_s3(self, batch_size=500, commit_each_batch=True):
        if not self._is_s3_hybrid():
            _logger.warning("S3 backfill skipped: hybrid storage mode is not active.")
            return 0
        domain = [
            ("type", "=", "binary"),
            ("res_model", "!=", False),
            ("s3_blob_name", "=", False),
            ("s3_mirror_pending", "=", False),
            "|",
            ("store_fname", "!=", False),
            ("db_datas", "!=", False),
        ]
        total = 0
        backfill = self._with_field_rows()
        while True:
            batch = backfill.search(domain, limit=batch_size)
            if not batch:
                break
            batch.s3_mirror_pending = True
            batch._s3_mirror_to_cloud()
            if commit_each_batch:
                self.env.cr.commit()  # pylint: disable=invalid-commit
            total += len(batch)
            _logger.info("S3 backfill: processed %s attachments so far.", total)
        _logger.info("S3 backfill finished: %s attachments processed.", total)
        return total

    @api.model
    def _cron_mirror_pending_to_s3(self, limit=100):
        if not self._is_s3_hybrid():
            return
        pending = self._with_field_rows().search(
            [("s3_mirror_pending", "=", True)], limit=limit
        )
        pending._s3_mirror_to_cloud()

    def _get_s3_info(self):
        match = S3_URL_PATTERN.fullmatch(self.url or "")
        if not match:
            raise ValidationError(
                self.env._("%s is not a valid Amazon S3 URL.", self.url)
            )
        return {
            "bucket_name": match["bucket_name"],
            "region": match["region"],
            "blob_name": unquote(match["blob_name"]),
        }

    def _generate_s3_url(self, blob_name):
        icp = self.env["ir.config_parameter"].sudo()
        return s3.object_url(
            icp.get_param(s3.PARAM_BUCKET), icp.get_param(s3.PARAM_REGION), blob_name
        )

    def _generate_s3_presigned_url(
        self, bucket_name, blob_name, method="get_object", expiration=300
    ):
        client = s3.get_client(self.env)
        params = {"Bucket": bucket_name, "Key": blob_name}
        return client.generate_presigned_url(
            method, Params=params, ExpiresIn=expiration
        )

    def _generate_cloud_storage_blob_name(self):
        if not self._is_s3_provider():
            return super()._generate_cloud_storage_blob_name()
        res_model = (self.res_model or "_orphan").replace(".", "_")
        res_id = self.res_id or 0
        short_uuid = uuid.uuid4().hex[:8]
        filename = self.name or "unnamed"
        return f"{res_model}/{res_id}/{self.id}_{short_uuid}_{filename}"

    def _generate_cloud_storage_url(self):
        if not self._is_s3_provider():
            return super()._generate_cloud_storage_url()
        blob_name = self._generate_cloud_storage_blob_name()
        return self._generate_s3_url(blob_name)

    def _generate_cloud_storage_download_info(self):
        if not self._is_s3_provider():
            return super()._generate_cloud_storage_download_info()
        info = self._get_s3_info()
        return {
            "url": self._generate_s3_presigned_url(
                info["bucket_name"],
                info["blob_name"],
                method="get_object",
                expiration=self._cloud_storage_download_url_time_to_expiry,
            ),
            "time_to_expiry": self._cloud_storage_download_url_time_to_expiry,
        }

    def _generate_cloud_storage_upload_info(self):
        if not self._is_s3_provider():
            return super()._generate_cloud_storage_upload_info()
        info = self._get_s3_info()
        return {
            "url": self._generate_s3_presigned_url(
                info["bucket_name"],
                info["blob_name"],
                method="put_object",
                expiration=self._cloud_storage_upload_url_time_to_expiry,
            ),
            "method": "PUT",
            "response_status": 200,
        }

    def unlink(self):
        if not self._s3_is_enabled():
            return super().unlink()
        blobs_by_bucket = defaultdict(list)
        hybrid_bucket = self._s3_bucket_name()
        hybrid_candidates = []
        for attach in self:
            if attach.type == "cloud_storage" and S3_URL_PATTERN.fullmatch(
                attach.url or ""
            ):
                try:
                    info = attach._get_s3_info()
                    blobs_by_bucket[info["bucket_name"]].append(info["blob_name"])
                except ValidationError:
                    pass
            elif attach.s3_blob_name and hybrid_bucket:
                hybrid_candidates.append(attach.s3_blob_name)
        res = super().unlink()
        if hybrid_candidates:
            still_used = set(
                self.sudo()
                ._with_field_rows()
                .search([("s3_blob_name", "in", hybrid_candidates)])
                .mapped("s3_blob_name")
            )
            for blob in set(hybrid_candidates):
                if blob not in still_used:
                    blobs_by_bucket[hybrid_bucket].append(blob)
        if blobs_by_bucket:
            client = s3.get_client(self.env)
            for bucket, blob_names in blobs_by_bucket.items():
                for batch in batched(blob_names, 1000, strict=False):
                    try:
                        client.delete_objects(
                            Bucket=bucket,
                            Delete={"Objects": [{"Key": k} for k in batch]},
                        )
                    except Exception:
                        _logger.warning(
                            "Failed to delete %d S3 blobs from bucket %s",
                            len(batch),
                            bucket,
                        )
        return res
