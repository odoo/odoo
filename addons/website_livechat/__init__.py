# -*- coding: utf-8 -*-
from . import controllers
from . import models

from odoo import api, SUPERUSER_ID


def _post_init_website_livechat(cr, registry):
    """ Chatbot operator partners must be 'website_published' to ensure
    their avatar is visible for end users. """

    env = api.Environment(cr, SUPERUSER_ID, {})
    env['chatbot.script'].search([]).operator_partner_id.write({
        'is_published': True
    })
