from . import models


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("pint_jp")
