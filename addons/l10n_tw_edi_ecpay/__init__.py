# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("tw_ecpay")
