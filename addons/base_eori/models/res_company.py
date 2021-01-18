# -*- coding: utf-8 -*-
# Copyright 2019-2021 XCLUDE AB (http://www.xclude.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# @author Daniel Stenlöv <info@xclude.se>

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    eori_validation = fields.Boolean(string='Verify EORI Numbers')
    eori_number = fields.Char(related='partner_id.eori_number', string="EORI Number", readonly=False)
