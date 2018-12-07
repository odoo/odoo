# -*- coding: utf-8 -*-	
# Part of Odoo. See LICENSE file for full copyright and licensing details.	

from odoo import fields, models	


class ResConfigSettings(models.TransientModel):	
    _inherit = 'res.config.settings'	

    invoice_is_snailmail = fields.Boolean(string='Send by Post with Snailmail', related='company_id.invoice_is_snailmail', readonly=False)
