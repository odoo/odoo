# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init_hook(env):
    email = env['ir.config_parameter'].get_param('hr_presence.hr_presence_control_email')
    ip = env['ir.config_parameter'].get_param('hr_presence.hr_presence_control_ip')

    if not email and not ip:
        env['ir.config_parameter'].sudo().set_param('hr_presence.hr_presence_control_email', True)
