# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools


def _l10n_it_edi_create_param(env):
    env['ir.config_parameter'].set_param('l10n_it_edi.proxy_user_edi_mode', 'prod')
