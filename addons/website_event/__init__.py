# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.safe_eval import safe_whitelist

from . import controllers
from . import models

safe_whitelist.add_function('odoo.addons.website_event.controllers.main.WebsiteEventController._slugify_tags')
