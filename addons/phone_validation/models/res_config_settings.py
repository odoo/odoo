# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    phone_international_format = fields.Selection(related="company_id.phone_international_format", required=True)
