# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    eori_validation = fields.Boolean(string='Verify EORI Numbers')
    eori_number = fields.Char(related='partner_id.eori_number', string="EORI Number", readonly=False)
