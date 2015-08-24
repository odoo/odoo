# -*- coding: utf-8 -*-

from openerp import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    uvt = fields.Float(string="UVT")
