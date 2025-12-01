# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard


# Rebind unbound action_partner_mass_mail on uninstall
def uninstall_hook(env):
    act_window = env.ref('mail.action_partner_mass_mail', raise_if_not_found=False)
    if act_window and not act_window.binding_model_id:
        act_window.binding_model_id = env['ir.model']._get_id('res.partner')
