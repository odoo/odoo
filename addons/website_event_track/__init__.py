# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def _post_init_hook(env):
    # app_icon is stored as an attachment, so it isn't computed for the
    # websites that exist when the module is installed
    env['website'].search([])._compute_app_icon()
