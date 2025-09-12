# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def _pos_online_payment_post_init(env):
    env['pos.config']._create_online_payment_demo()
