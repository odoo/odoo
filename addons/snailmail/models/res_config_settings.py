# -*- coding: utf-8 -*-	
# Part of Odoo. See LICENSE file for full copyright and licensing details.	

from odoo import fields, models	


class ResConfigSettings(models.TransientModel):	
    _inherit = 'res.config.settings'	

    snailmail_color = fields.Boolean(string='Print In Color', related='company_id.snailmail_color', related_inverse=True)
    snailmail_cover = fields.Boolean(string='Add a Cover Page', related='company_id.snailmail_cover', related_inverse=True)
    snailmail_duplex = fields.Boolean(string='Print Both sides', related='company_id.snailmail_duplex', related_inverse=True)
