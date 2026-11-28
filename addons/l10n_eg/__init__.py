from . import models


def _l10n_eg_post_init(env):
    env['res.lang']._activate_and_install_lang('ar_001')
