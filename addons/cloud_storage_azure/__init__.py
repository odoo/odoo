# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def uninstall_hook(env):
    env['res.config.settings']._check_cloud_storage_uninstallable('azure')

    env['ir.config_parameter'].set_param('cloud_storage_provider', False)
    env['ir.config_parameter'].search([('key', 'in', [
        'cloud_storage_azure_container_name',
        'cloud_storage_azure_account_name',
        'cloud_storage_azure_tenant_id',
        'cloud_storage_azure_client_id',
        'cloud_storage_azure_client_secret',
    ])]).unlink()
