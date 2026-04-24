# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def pos_history_post_init(env):
    # Enable track history when German localization is installed, as it is a legal requirement.
    if 'l10n_de_pos_cert' in env['ir.module.module']._installed():
        env['pos.config'].search([('l10n_de_fiskaly_tss_id', '!=', False)]).is_history_tracked = True
