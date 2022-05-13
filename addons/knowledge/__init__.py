# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from odoo import api, SUPERUSER_ID


def _init_private_article_per_user(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.users'].search([('partner_share', '=', False)])._generate_tutorial_articles()
