# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def _l10n_tr_post_init(env):
    # Activate the Turkish language on module installation
    env['res.lang']._activate_lang('tr_TR')
