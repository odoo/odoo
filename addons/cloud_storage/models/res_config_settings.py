# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields
from odoo.exceptions import UserError


DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE = 20_000_000  # 20MB


class ResConfigSettings(models.TransientModel):
    """
    Instructions:
    cloud_storage_provider: Once set, new attachments from the web client can
        be created as cloud storage attachments. Once changed, all attachments
        stored in the old cloud storage provider cannot be fetched. Please
        migrate those cloud storage blobs and the url field of their
        ir.attachment records before change.
    cloud_storage_mim_file_size: a soft limit for the file size that can be
        uploaded as the cloud storage attachments for web client.
    """
    _inherit = 'res.config.settings'

    cloud_storage_provider = fields.Selection(
        selection=[],
        string='Cloud Storage Provider for new attachments',
        config_parameter='cloud_storage_provider',
    )

    cloud_storage_min_file_size_mb = fields.Float(string='Minimum File Size (MB)')

    cloud_storage_min_file_size = fields.Integer(
        string='Minimum File Size (bytes)',
        help='''webclient can upload files larger than the minimum file size
        (in bytes) as url attachments to the server and then upload the file to
        the cloud storage.''',
        config_parameter='cloud_storage_min_file_size',
        default=DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE,
    )

    def _setup_cloud_storage_provider(self):
        """
        Setup the cloud storage provider and check the validity of the account
        info after saving the config in settings.
        return: None
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
        ICP = self.env['ir.config_parameter']
        res['cloud_storage_min_file_size_mb'] = int(ICP.get_param('cloud_storage_min_file_size', DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE)) / 1000000
        return res

    def set_values(self):
        ICP = self.env['ir.config_parameter']
        cloud_storage_configuration_before = self._get_cloud_storage_configuration()
        cloud_storage_provider_before = ICP.get_param('cloud_storage_provider')
        if cloud_storage_provider_before and self.cloud_storage_provider != cloud_storage_provider_before:
            self._check_cloud_storage_uninstallable()
        self.cloud_storage_min_file_size = int(self.cloud_storage_min_file_size_mb * 1000000)
        super().set_values()
        cloud_storage_configuration = self._get_cloud_storage_configuration()
        if not cloud_storage_configuration and self.cloud_storage_provider:
            raise UserError(self.env._('Please configure the Cloud Storage before enabling it'))
        if cloud_storage_configuration and cloud_storage_configuration != cloud_storage_configuration_before:
            self._setup_cloud_storage_provider()
