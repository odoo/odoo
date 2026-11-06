from . import models
from . import tools


def _l10n_np_post_init(env):
    env['res.lang']._activate_and_install_lang('ne_NP')
