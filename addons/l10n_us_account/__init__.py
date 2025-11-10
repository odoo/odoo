# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The purpose of l10n_us_account is to automatically trigger the installation of l10n_us for the new US databases
# Also, l10n_us_account should contains all the accounting-related dependencies of US localization package
from . import models


def uninstall_hook(env):
    """Remove ir.model.data records for account.asset that match account_asset_us_.*"""
    env['ir.model.data'].search([
        ('model', '=', 'account.asset'),
        ('name', 'like', '%account_asset_us_%'),
    ]).unlink()
