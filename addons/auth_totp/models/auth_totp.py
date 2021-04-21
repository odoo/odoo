# -*- coding: utf-8 -*-
from odoo import models


class AuthTotpDevice(models.Model):

    # init is overriden in res.users.apikeys to create a secret column 'key'
    # use a different model to benefit from the secured methods while not mixing
    # two different concepts

    _name = "auth_totp.device"
    _inherit = "res.users.apikeys"
    _description = "Authentication Device"
    _auto = False
