# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_websocket_worker_version(self):
        bundle_name = 'bus.websocket_worker_assets'
        files, _ = self.env['ir.qweb']._get_asset_content(bundle_name)
        asset = self.env['ir.qweb']._get_asset_bundle(bundle_name, files)
        return asset.version

    def session_info(self):
        result = super().session_info()
        result['dbuuid'] = request.env['ir.config_parameter'].sudo().get_param('database.uuid')
        result['websocket_worker_version'] = self._get_websocket_worker_version()
        return result

    def get_frontend_session_info(self):
        result = super().get_frontend_session_info()
        result['dbuuid'] = request.env['ir.config_parameter'].sudo().get_param('database.uuid')
        result['websocket_worker_version'] = self._get_websocket_worker_version()
        return result
