# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from .res_config_settings import DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('cloud_storage_provider'):
            res['cloud_storage_min_file_size'] = int(ICP.get_param('cloud_storage_min_file_size', DEFAULT_CLOUD_STORAGE_MIN_FILE_SIZE))
            res['cloud_storage_unsupported_models'] = self.env['ir.attachment']._get_cloud_storage_unsupported_models()
        return res
