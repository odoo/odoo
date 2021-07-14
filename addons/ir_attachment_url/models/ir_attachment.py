# Copyright 2016-2018 Ildar Nasyrov <https://it-projects.info/team/iledarn>
# Copyright 2016-2018,2020-2021 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2020 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import base64
import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):

    _inherit = "ir.attachment"

    @api.depends("store_fname", "db_datas")
    def _compute_raw(self):
        url_records = self.filtered(lambda r: r.type == "url" and r.url)
        for attach in url_records:
            r = requests.get(attach.url, timeout=5)
            attach.raw = r.content

        super(IrAttachment, self - url_records)._compute_raw()

    def _filter_protected_attachments(self):
        return self.filtered(
            lambda r: r.res_model not in ["ir.ui.view", "ir.ui.menu"]
            and not r.name.startswith("/web/content/")
            and not r.name.startswith("/web/static/")
        )

    @api.model_create_multi
    def create(self, vals_list):
        url_fields = self.env.context.get("ir_attachment_url_fields")
        if url_fields:
            url_fields = url_fields.split(",")
        self._set_where_to_store(vals_list)
        for values in vals_list:
            if (
                url_fields
                and values.get("type") != "url"
                and not values.get("url")
                and values.get("res_model")
                and values.get("res_field")
                and values.get("datas")
            ):
                full_field_name = values["res_model"] + "." + values["res_field"]
                if full_field_name in url_fields:
                    values["url"] = values["datas"]
                    values["type"] = "url"
                    del values["datas"]
            bucket = values.pop("_bucket", None)
            if (
                bucket
                and values.get("datas")
                and values.get("res_model") not in ["ir.ui.view", "ir.ui.menu"]
            ):
                values = self._check_contents(values)
                data = values.pop("datas")
                filename = values.get("name")
                mimetype = values.pop("mimetype")
                values.update(
                    self._get_datas_related_values_with_bucket(
                        bucket, data, filename, mimetype
                    )
                )
        return super(IrAttachment, self).create(vals_list)

    def _get_datas_related_values_with_bucket(
        self, bucket, data, filename, mimetype, checksum=None
    ):
        bin_data = base64.b64decode(data) if data else b""
        if not checksum:
            checksum = self._compute_checksum(bin_data)
        fname, url = self._file_write_with_bucket(
            bucket, bin_data, filename, mimetype, checksum
        )
        return {
            "file_size": len(bin_data),
            "checksum": checksum,
            "index_content": self._index(bin_data, mimetype),
            "store_fname": fname,
            "db_datas": False,
            "type": "binary",
            "url": url,
        }

    def _set_where_to_store(self, vals_list):
        pass

    def _file_write_with_bucket(self, bucket, bin_data, filename, mimetype, checksum):
        raise NotImplementedError(
            "No _file_write handler for bucket object {}".format(repr(bucket))
        )

    def _write_records_with_bucket(self, bucket):
        for attach in self:
            vals = self._get_datas_related_values_with_bucket(
                bucket, attach.datas, attach.name, attach.mimetype
            )
            super(IrAttachment, attach.sudo()).write(vals)

    def _force_storage_with_bucket(self, bucket, domain):
        attachment_ids = self._search(domain)

        _logger.info(
            "Approximately %s attachments to store to %s"
            % (len(attachment_ids), repr(bucket))
        )
        for attach in map(self.browse, attachment_ids):
            is_protected = not bool(attach._filter_protected_attachments())

            if is_protected:
                _logger.info("ignoring protected attachment %s", repr(attach))
                continue
            else:
                _logger.info("storing %s", repr(attach))

            old_store_fname = attach.store_fname
            data = self._file_read(old_store_fname)
            bin_data = base64.b64decode(data) if data else b""
            checksum = (
                self._compute_checksum(bin_data)
                if not attach.checksum
                else attach.checksum
            )

            new_store_fname, url = self._file_write_with_bucket(
                bucket, bin_data, attach.name, attach.mimetype, checksum
            )
            attach.write({"store_fname": new_store_fname, "url": url})
            self._file_delete(old_store_fname)
