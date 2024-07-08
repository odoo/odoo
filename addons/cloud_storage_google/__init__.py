# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def uninstall_hook(env):
    ICP = env['ir.config_parameter']
    if ICP.get_param('cloud_storage_provider') == 'google':
        env['res.config.settings']._check_cloud_storage_uninstallable()
        ICP.set_param('cloud_storage_provider', False)
    ICP.search([('key', 'in', [
        'cloud_storage_google_bucket_name',
        'cloud_storage_google_account_info',
    ])]).unlink()
