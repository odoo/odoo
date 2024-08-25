# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


from odoo.service.security import SESSION_TOKEN_FIELDS

SESSION_TOKEN_FIELDS |= {'oauth_access_token'}


def uninstall_hook(env):
    SESSION_TOKEN_FIELDS.discard('oauth_access_token')
