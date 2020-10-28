# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    fiskaly_key = fields.Char(string="Fiskaly API key")
    fiskaly_secret = fields.Char(string="Fiskaly API secret")
