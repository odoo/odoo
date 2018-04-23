# -*- coding: utf-8 -*-	
# Part of Odoo. See LICENSE file for full copyright and licensing details.	
	
from odoo import fields, models, api	
	
class ResConfigSettings(models.TransientModel):	
    _inherit = 'res.config.settings'	
	
    snailmail_color = fields.Boolean(string='color', related='company_id.snailmail_color')	
    snailmail_duplex = fields.Boolean(string='Both sides', related='company_id.snailmail_duplex')
