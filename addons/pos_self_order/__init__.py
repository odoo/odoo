# -*- coding: utf-8 -*-

from . import controllers
from . import models
from . import tests

def _post_self_order_post_init(env):
    sessions = env['pos.session'].search([('state', '!=', 'closed')])
    if len(sessions) > 0:
        env['pos.session']._create_pos_self_sessions_sequence(sessions)
