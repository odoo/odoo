# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def uninstall_hook(env):
    env['res.config.settings']._check_cloud_storage_uninstallable('google')

    env['ir.config_parameter'].sudo().set_param('cloud_storage_provider', False)
    env['ir.config_parameter'].sudo().search([('key', 'in', [
        'cloud_storage_google_bucket_name',
        'cloud_storage_google_account_info',
    ])]).unlink()
