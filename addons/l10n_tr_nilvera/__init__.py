from . import models


def _l10n_tr_nilvera_post_init(env):
    env['res.lang']._activate_and_update_lang('tr_TR')
