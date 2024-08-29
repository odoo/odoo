# -*- coding: utf-8 -*-
from odoo.addons import base

from odoo import api, fields, models


class ResUsersLog(models.Model, base.ResUsersLog):

    create_uid = fields.Integer(index=True)
    ip = fields.Char(string="IP Address")
