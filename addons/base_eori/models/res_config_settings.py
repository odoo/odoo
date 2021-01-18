# -*- coding: utf-8 -*-
# Copyright 2019-2021 XCLUDE AB (http://www.xclude.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# @author Daniel Stenlöv <info@xclude.se>

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    eori_validation = fields.Boolean(related='company_id.eori_validation', readonly=False, string='Verify EORI Number')
