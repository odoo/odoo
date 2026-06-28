# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def uninstall_hook(env):
    if rule := env.ref('gamification.gamification_badge_user_access', raise_if_not_found=False):
        rule.active = True
