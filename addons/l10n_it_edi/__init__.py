import logging

from odoo.tools.safe_eval import safe_whitelist

from . import controllers, models, tools

_logger = logging.getLogger(__name__)


def _l10n_it_edi_post_init(env):
    env['ir.config_parameter'].set_str('l10n_it_edi.proxy_user_edi_mode', 'prod')


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("it_edi_xml")


safe_whitelist.add_function('odoo.addons.l10n_it_edi.models.account_move.AccountMove._l10n_it_edi_get_formatters.<locals>.*')
