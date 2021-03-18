# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    eori_validation = fields.Boolean(related='company_id.eori_validation', readonly=False, string='Verify EORI Number')
