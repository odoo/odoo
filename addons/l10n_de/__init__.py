# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report


def _post_init_hook(env):
    env['res.groups']._activate_group_account_secured()
