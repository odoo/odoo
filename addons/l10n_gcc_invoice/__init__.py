from . import models


def _l10n_gcc_invoice_post_init(env):
    env['res.lang']._activate_lang('ar_001')
