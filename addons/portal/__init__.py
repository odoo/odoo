# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Updating mako environement in order to be able to use slug
try:
    from odoo.tools.rendering_tools import template_env_globals
    from odoo.http import request

    template_env_globals.update({
        'slug': lambda value: request.env['ir.http']._slug(value)  # noqa: PLW0108
    })
except ImportError:
    pass

from . import controllers
from . import models
from . import utils
from . import wizard
