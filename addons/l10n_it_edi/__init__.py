import logging

from . import controllers, models, tools

_logger = logging.getLogger(__name__)


def _l10n_it_edi_post_init(env):
    env['ir.config_parameter'].set_param('l10n_it_edi.proxy_user_edi_mode', 'prod')


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("it_edi_xml")
