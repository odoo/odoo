# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def _l10n_uk_post_init(env):
    bacs_module = env['ir.module.module'].search([('name', '=', 'l10n_uk_bacs'), ('state', '=', 'uninstalled')])
    if bacs_module:
        bacs_module.sudo().button_install()
