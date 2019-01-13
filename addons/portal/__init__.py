# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Updating mako environement in order to be able to use slug
try:
    from odoo.addons.mail.models.mail_template import mako_template_env, mako_safe_template_env
    from odoo.addons.http_routing.models.ir_http import slug

    mako_template_env.globals.update({
        'slug': slug,
    })

    mako_safe_template_env.globals.update({
        'slug': slug,
    })
except ImportError:
    pass

from . import controllers
from . import models
from . import wizard
