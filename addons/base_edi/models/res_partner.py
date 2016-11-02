# -*- coding: utf-8 -*-

from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    template = fields.Many2one('edi.template', string='XML invoice template')