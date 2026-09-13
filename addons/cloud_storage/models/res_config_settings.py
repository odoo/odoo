from odoo import api, fields, models
from odoo.exceptions import UserError

DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE = 20_000_000  # 20MB


class ResConfigSettings(models.TransientModel):
    """Cloud storage settings for web client attachments."""

    _inherit = "res.config.settings"

    cloud_storage_provider = fields.Selection(
        selection=[],
        string="Cloud Storage Provider for new attachments",
        config_parameter="cloud_storage_provider",
    )

    cloud_storage_min_file_size_mb = fields.Float(string="Minimum File Size (MB)")

    cloud_storage_min_file_size = fields.Integer(
        string="Minimum File Size (bytes)",
        default=DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE,
        config_parameter="cloud_storage_min_file_size",
        help="""webclient can upload files larger than the minimum file size
        (in bytes) as url attachments to the server and then upload the file to
        the cloud storage.""",
    )

    def _setup_cloud_storage_provider(self):
        """
        Setup the cloud storage provider and check the validity of the account
        info after saving the config in settings.
        """
        pass

    def _get_cloud_storage_configuration(self):
        """
        Return the configuration for the cloud storage provider. If the cloud
        storage provider is not fully configured, return an empty dict.
        :return: A configuration dict
        """
        return {}

    def _check_cloud_storage_uninstallable(self):
        """
        Check if the cloud storages provider is used by any attachments
        :raise UserError: when the cloud storage provider cannot be uninstalled
        """
        pass

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env["ir.config_parameter"]
        res["cloud_storage_min_file_size_mb"] = (
            int(
                ICP.get_param(
                    "cloud_storage_min_file_size", DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE
                )
            )
            / 1000000
        )
        return res

    def set_values(self):
        ICP = self.env["ir.config_parameter"]
        cloud_storage_configuration_before = self._get_cloud_storage_configuration()
        cloud_storage_provider_before = ICP.get_param("cloud_storage_provider")
        if (
            cloud_storage_provider_before
            and self.cloud_storage_provider != cloud_storage_provider_before
        ):
            self._check_cloud_storage_uninstallable()
        self.cloud_storage_min_file_size = int(
            self.cloud_storage_min_file_size_mb * 1000000
        )
        super().set_values()
        cloud_storage_configuration = self._get_cloud_storage_configuration()
        if not cloud_storage_configuration and self.cloud_storage_provider:
            raise UserError(
                self.env._("Please configure the Cloud Storage before enabling it")
            )
        if (
            cloud_storage_configuration
            and cloud_storage_configuration != cloud_storage_configuration_before
        ):
            self._setup_cloud_storage_provider()
