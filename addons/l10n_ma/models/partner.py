# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit= 'res.partner'
    
    ice = fields.Char(string="ICE", size=15, required=False)
