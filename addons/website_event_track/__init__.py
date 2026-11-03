# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def _link_default_track_stages(env):
    """ Events existing before the installation are computed before the
    default stages are loaded: give them the default stages. """
    events = env['event.event'].with_context(active_test=False).search([('track_stage_ids', '=', False)])
    if events:
        events.track_stage_ids = env['event.event']._get_default_track_stages()
