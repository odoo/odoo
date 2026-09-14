from . import models, wizard


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("pint_ae")
