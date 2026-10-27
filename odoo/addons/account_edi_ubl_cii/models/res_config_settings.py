# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_is_ubl_cii = fields.Boolean(string='Peppol format', related='company_id.invoice_is_ubl_cii', readonly=False)
