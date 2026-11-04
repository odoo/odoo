# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def post_init_hook(env):
    env['res.company']._check_hr_presence_control(True)


def uninstall_hook(env):
    env['res.company']._check_hr_presence_control(False)
