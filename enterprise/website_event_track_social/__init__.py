# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init(env):
    # Do not send push notification for old event tracks
    env['event.track'].search([]).write({
        'push_reminder': False,
        'push_reminder_delay': 0,
    })
