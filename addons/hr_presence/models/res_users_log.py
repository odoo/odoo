# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons import base


class ResUsersLog(base.ResUsersLog):

    create_uid = fields.Integer(index=True)
    ip = fields.Char(string="IP Address")
