# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard


def _sync_light_users_post_init(env):
    # Grant the time-off employee group to Light users provisioned before install.
    env['res.users']._sync_light_user_groups()
