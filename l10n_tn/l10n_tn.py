# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class res_company(models.Model):
    _inherit = 'res.company'

    
    siret=fields.Char('SIRET', size=14)
    ape=fields.Char('APE')
    