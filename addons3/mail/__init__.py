# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools
from . import wizard
from . import controllers
from . import populate

def _mail_post_init(env):
    env['mail.alias.domain']._migrate_icp_to_domain()
