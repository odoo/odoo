# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    extract_in_invoice_digitalization_mode = fields.Selection(related='company_id.extract_in_invoice_digitalization_mode',
                                                              string='Vendor Bills', readonly=False)
    extract_out_invoice_digitalization_mode = fields.Selection(related='company_id.extract_out_invoice_digitalization_mode',
                                                               string='Customer Invoices', readonly=False)
    extract_single_line_per_tax = fields.Boolean(related='company_id.extract_single_line_per_tax',
                                                 string='Single Invoice Line Per Tax', readonly=False)
