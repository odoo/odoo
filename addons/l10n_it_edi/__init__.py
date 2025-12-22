# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("it_edi_xml")
