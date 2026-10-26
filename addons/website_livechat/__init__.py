# -*- coding: utf-8 -*-
from . import controllers
from . import models


def _post_init_hook(env):
    # The theme colors can only be read once this module's scss export is
    # part of the registry, which is not the case while its data is loaded.
    env.transaction.invalidate_ormcache("assets")
    env["website"].search([("channel_id", "!=", False)])._seed_livechat_theme_colors()
