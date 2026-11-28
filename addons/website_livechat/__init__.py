# -*- coding: utf-8 -*-
from . import controllers
from . import models


def _post_init_hook(env):
    # Existing channels keep their look, except the website channels with the
    # default colors, which follow the theme. The upgrade script applies the
    # same rule to the colors of the previous versions.
    website_channels = env["website"].search([("channel_id", "!=", False)]).channel_id
    channels = env["im_livechat.channel"].search([])
    (channels - website_channels.filtered(lambda channel: channel._has_default_colors())).follow_website_theme = False
