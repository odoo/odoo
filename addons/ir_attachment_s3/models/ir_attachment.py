# Copyright 2016-2018 Ildar Nasyrov <https://it-projects.info/team/iledarn>
# Copyright 2016-2018,2021 Ivan Yelizariev <https://twitter.com/yelizariev>
# Copyright 2019 Alexandr Kolushov <https://it-projects.info/team/KolushovAlexandr>
# Copyright 2019 Rafis Bikbov <https://it-projects.info/team/RafiZz>
# Copyright 2019 Dinar Gabbasov <https://it-projects.info/team/GabbasovDinar>
# Copyright 2019-2020 Eugene Molotov <https://it-projects.info/team/em230418>
# License MIT (https://opensource.org/licenses/MIT).

import base64
import logging

from odoo import _, models
from odoo.exceptions import MissingError
from odoo.tools.safe_eval import safe_eval

from .res_config_settings import NotAllCredentialsGiven

_logger = logging.getLogger(__name__)

PREFIX = "s3://"


def is_s3_bucket(bucket):
    meta = getattr(bucket, "meta", None)
    return meta and getattr(meta, "service_name", None) == "s3"


class IrAttachment(models.Model):

    _inherit = "ir.attachment"

    def _inverse_datas(self):
        condition = self.env["res.config.settings"]._get_s3_settings(
            "s3.condition", "S3_CONDITION"
        )
        if condition and not self.env.context.get("force_s3"):
            condition = safe_eval(condition, mode="eval")
            s3_records = self.sudo().search([("id", "in", self.ids)] + condition)
        else:
            # if there is no condition or force_s3 in context
            # then store all attachments on s3
            s3_records = self

        if s3_records:

            try:
                bucket = self.env["res.config.settings"].get_s3_bucket()
            except NotAllCredentialsGiven:
                _logger.info("something wrong on aws side, keep attachments as usual")
                s3_records = self.env[self._name]
            except Exception:
                _logger.exception(
                    "Something bad happened with S3. Keeping attachments as usual"
                )
                s3_records = self.env[self._name]
            else:
                s3_records = s3_records._filter_protected_attachments()
                s3_records = s3_records.filtered(lambda r: r.type != "url")
                s3_records._write_records_with_bucket(bucket)

        return super(IrAttachment, self - s3_records)._inverse_datas()

    def _file_read(self, fname):
        if not fname.startswith(PREFIX):
            return super(IrAttachment, self)._file_read(fname)

        bucket = self.env["res.config.settings"].get_s3_bucket()

        file_id = fname[len(PREFIX) :]
        _logger.debug("reading file with id {}".format(file_id))

        obj = bucket.Object(file_id)
        data = obj.get()

        return base64.b64encode(b"".join(data["Body"]))

    def _file_delete(self, fname):
        if not fname.startswith(PREFIX):
            return super(IrAttachment, self)._file_delete(fname)

        bucket = self.env["res.config.settings"].get_s3_bucket()

        file_id = fname[len(PREFIX) :]
        _logger.debug("deleting file with id {}".format(file_id))

        obj = bucket.Object(file_id)
        obj.delete()

    def force_storage_s3(self):
        try:
            bucket = self.env["res.config.settings"].get_s3_bucket()
        except NotAllCredentialsGiven:
            if self.env.context.get("module") == "general_settings":
                raise MissingError(
                    _(
                        "Some of the S3 connection credentials are missing.\n Don't forget to click the ``[Save]`` button after any changes you've made"
                    )
                )
            else:
                raise

        s3_condition = self.env["ir.config_parameter"].sudo().get_param("s3.condition")
        condition = s3_condition and safe_eval(s3_condition, mode="eval") or []

        return self._force_storage_with_bucket(
            bucket,
            [
                ("type", "!=", "url"),
                ("id", "!=", 0),
                ("store_fname", "not ilike", PREFIX),
                ("store_fname", "!=", False),
                ("res_model", "not in", ["ir.ui.view", "ir.ui.menu"]),
            ]
            + condition,
        )

    def _set_where_to_store(self, vals_list):
        bucket = None
        try:
            bucket = self.env["res.config.settings"].get_s3_bucket()
        except NotAllCredentialsGiven:
            _logger.info("Could not get S3 bucket. Not all credentials given")
        except Exception:
            _logger.exception("Could not get S3 bucket")

        if not bucket:
            return super(IrAttachment, self)._set_where_to_store(vals_list)

        # TODO: тут игнорируется s3 condition и соотвествующий bucket пишется везде
        for values in vals_list:
            values["_bucket"] = bucket

        return super(IrAttachment, self)._set_where_to_store(vals_list)

    def _file_write_with_bucket(self, bucket, bin_data, filename, mimetype, checksum):
        # make sure, that given bucket is s3 bucket
        if not is_s3_bucket(bucket):
            return super(IrAttachment, self)._file_write_with_bucket(
                bucket, bin_data, filename, mimetype, checksum
            )

        file_id = "odoo/{}".format(checksum)

        bucket.put_object(
            Key=file_id,
            Body=bin_data,
            ACL="public-read",
            ContentType=mimetype,
            ContentDisposition='attachment; filename="%s"' % filename,
        )

        _logger.debug("uploaded file with id {}".format(file_id))
        obj_url = self.env["res.config.settings"].get_s3_obj_url(bucket, file_id)
        return PREFIX + file_id, obj_url
