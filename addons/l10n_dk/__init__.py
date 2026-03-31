from . import models
from . import tools
from . import wizard


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("oioubl_21")
