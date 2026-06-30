# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import tools

def pre_init_hook(env):
    view = env.ref("account_edi_ubl_cii.account_move_send_form")
    if "ubl_partner_warning" not in view.arch:
        view.reset_arch(mode='hard')
