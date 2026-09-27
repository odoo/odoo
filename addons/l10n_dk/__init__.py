from . import models
from . import tools
from . import wizard


def _post_init_nemhandel(env):
    if env['ir.config_parameter'].sudo().get_bool('database.is_neutralized'):
        env['ir.config_parameter'].sudo().set_str('l10n_dk.edi.mode', 'test')


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("oioubl_21")
