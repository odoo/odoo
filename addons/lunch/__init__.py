# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report


def _sync_light_users_post_init(env):
    # Grant the lunch self-service group to Light users provisioned before install.
    env['res.users']._sync_light_user_groups()
