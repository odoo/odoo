# -*- coding: utf-8 -*-

from odoo import models, fields


class DemoAccessRights(models.Model):
    _name = 'demo.access.rights'
    _rec_name = 'name'

    name = fields.Char('Name', required=True)

