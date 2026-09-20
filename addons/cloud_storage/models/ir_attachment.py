import logging
import uuid

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import Stream

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"
    _cloud_storage_upload_url_time_to_expiry = 300  # 300 seconds
    _cloud_storage_download_url_time_to_expiry = 300  # 300 seconds

    type = fields.Selection(
        selection_add=[("cloud_storage", "Cloud Storage")],
        ondelete={"cloud_storage": "set url"},
    )

    def _to_http_stream(self):
        if (
            self.type == "cloud_storage"
            and self.env["res.config.settings"]._get_cloud_storage_configuration()
        ):
            self.check_singleton()
            info = self._generate_cloud_storage_download_info()
            stream = Stream(type="url", url=info["url"])
            if "time_to_expiry" in info:
                # cache the redirection until 10 seconds before the expiry
                stream.max_age = max(info["time_to_expiry"] - 10, 0)
            return stream
        return super()._to_http_stream()

    def _post_add_create(self, **kwargs):
        super()._post_add_create(**kwargs)
        if kwargs.get("cloud_storage"):
            if (
                not self.env["ir.config_parameter"]
                .sudo()
                .get_param("cloud_storage_provider")
            ):
                raise UserError(_("Cloud Storage is not enabled"))
            for record in self:
                record.write(
                    {
                        "raw": False,
                        "type": "cloud_storage",
                        "url": record._generate_cloud_storage_url(),
                    }
                )

    def _fetch_content(self, size=None):
        """Download the blob a provider holds, so the bytes exist for a reader.

        `raw` and `_get_content_prefix` answer `b""` for a `cloud_storage`
        attachment: this database keeps the URL, not the file. Everything that
        turns bytes into text -- indexation, the document layer, OCR -- reads
        one of those two and therefore reads a cloud-stored document as an
        empty one, with no error anywhere. Fetching here puts the blob back in
        front of every one of them without any of them learning about clouds.

        `size` is served with a Range request, so a caller that only needs a
        header does not pull a gigabyte across the network.
        """
        if self.type != "cloud_storage":
            return super()._fetch_content(size)
        self.check_singleton()
        url = self._generate_cloud_storage_download_info()["url"]
        headers = {"Range": f"bytes=0-{size - 1}"} if size else {}
        response = requests.get(url, timeout=60, headers=headers)
        response.raise_for_status()
        return response.content

    def _migrate_remote_to_local(self):
        if self.type != "cloud_storage":
            return super()._migrate_remote_to_local()
        url = self._generate_cloud_storage_download_info()["url"]
        response = self.env["ir.egress"].request(
            "GET", url, purpose="cloud_storage", timeout=10, max_bytes=None
        )
        response.raise_for_status()
        if response.status_code != 200:
            raise ValidationError(
                _(
                    "Failed to download attachment (%(id)s) from cloud: %(code)s - %(reason)s",
                    id=self.id,
                    code=response.status_code,
                    reason=response.reason,
                )
            )
        attachment_data = response.content
        _logger.info(
            "Migrating attachment (%s) with url (%s) from cloud_storage to binary.",
            self.id,
            self.url,
        )
        self.write(
            {
                "type": "binary",
                "url": False,
                "raw": attachment_data,
            }
        )
        return True

    def _generate_cloud_storage_blob_name(self):
        """
        Generate a unique blob name for the attachment

        :return: A unique blob name str
        """
        return f"{self.id}/{uuid.uuid4()}/{self.name}"

    # Implement the following methods for each cloud storage provider.
    def _generate_cloud_storage_url(self):
        """
        Generate a cloud blob url without signature or token for the attachment.
        This url is only used to identify the cloud blob.

        :return: A cloud blob url str
        """
        raise NotImplementedError

    def _generate_cloud_storage_download_info(self):
        """
        Generate the download info for the public client to directly download
        the attachment's blob from the cloud storage.

        :return: An download_info dictionary containing:

            url
                cloud storage url with permission to download the file
            time_to_expiry
                the time in seconds before the download url expires
        """
        raise NotImplementedError

    def _generate_cloud_storage_upload_info(self):
        """
        Generate the upload info for the public client to directly upload a
        file to the cloud storage.

        :return: An upload_info dictionary containing:

            url
                cloud storage url with permission to upload the file
            method
                the request method used to upload the file
            response_status
                the status of the response for a successful upload request
            [Optionally] headers
                a dictionary of headers to be added to the upload request
        """
        raise NotImplementedError

    def _get_cloud_storage_unsupported_models(self):
        # A main attachment is read back by business code (OCR, EDI, previews),
        # so it must keep its bytes on the server.
        return list(
            self.env.registry.get_descendants(
                ["mixin.mail.thread.main.attachment"], "_inherit", "_inherits"
            )
        )

    def _get_zip_detached_reader(self):
        if self.type != "cloud_storage":
            return super()._get_zip_detached_reader()
        url = self._generate_cloud_storage_download_info()["url"]

        def read_blocks(block_size):
            with self.env["ir.egress"].request(
                "GET",
                url,
                purpose="cloud_storage",
                stream=True,
                timeout=30,
                max_bytes=None,
            ) as response:
                response.raise_for_status()
                yield from response.iter_content(block_size)

        return read_blocks
