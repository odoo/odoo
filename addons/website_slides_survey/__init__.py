# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers


def uninstall_hook(env):
    slide = env.ref('website_slides.badge_data_certification_goal', raise_if_not_found=False)
    if slide:
        slide.domain = "[('completed', '=', True), (0, '=', 1)]"
