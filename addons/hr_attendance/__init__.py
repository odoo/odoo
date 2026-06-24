# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def post_init_hook(env):
    env['res.company']._check_hr_presence_control(True)
    # Grant the own-attendance group to Light users provisioned before install.
    env['res.users']._sync_maximal_light_user_groups()


def uninstall_hook(env):
    env['res.company']._check_hr_presence_control(False)
