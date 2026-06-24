# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import receipt
from . import models
from . import report
from . import controllers
from . import wizard


def _sync_light_users_post_init(env):
    # Grant the POS self-service group to Light users provisioned before install.
    env['res.users']._sync_maximal_light_user_groups()
