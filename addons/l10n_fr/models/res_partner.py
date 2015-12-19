# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    siret = fields.Char()
