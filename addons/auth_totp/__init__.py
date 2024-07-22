# -*- coding: utf-8 -*-
from . import controllers
from . import models
from . import wizard

from odoo.service.security import SESSION_TOKEN_FIELDS

SESSION_TOKEN_FIELDS |= {'totp_secret'}


def uninstall_hook(env):
    SESSION_TOKEN_FIELDS.discard('totp_secret')
