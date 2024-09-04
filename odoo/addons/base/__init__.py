# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .controllers import *
from .models import *
from .populate import *
from .report import *
from .wizard import *


def post_init(env):
    """Rewrite ICP's to force groups"""
    env['ir.config_parameter'].init(force=True)
