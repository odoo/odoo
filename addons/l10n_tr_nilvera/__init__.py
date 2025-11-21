from . import models


def _l10n_tr_nilvera_post_init(env):
    env["res.lang"]._activate_and_install_lang("tr_TR")


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("ubl_tr")
