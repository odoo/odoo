# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.rendering_tools import template_env_globals
from odoo.tools.safe_eval import safe_whitelist
from odoo.http import request

template_env_globals.update({
    'slug': lambda value: request.env['ir.http']._slug(value)  # noqa: PLW0108
})

from . import controllers
from . import models
from . import utils
from . import wizard

safe_whitelist.add_function('odoo.addons.portal.controllers.portal.get_error')
safe_whitelist.add_function('odoo.addons.portal.models.ir_qweb.IrQweb._prepare_frontend_environment.<locals>.*')
