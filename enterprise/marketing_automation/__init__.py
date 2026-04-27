# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard


def uninstall_hook(env):
    # remove reference to mailing.mailing use_in_marketing_automation field
    act_window = env.ref('mass_mailing.mailing_mailing_action_mail', False)
    if act_window and act_window.domain and 'use_in_marketing_automation' in act_window.domain:
        act_window.domain = [('mailing_type', '=', 'mail')]
