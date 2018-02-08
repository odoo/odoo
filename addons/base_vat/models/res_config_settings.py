# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vat_check_vies = fields.Boolean(related='company_id.vat_check_vies',
        string='Verify VAT Numbers')
