# -*- coding: utf-8 -*-	
# Part of Odoo. See LICENSE file for full copyright and licensing details.	

from odoo import fields, models	


class ResConfigSettings(models.TransientModel):	
    _inherit = 'res.config.settings'	

    snailmail_color = fields.Boolean(string='Print In Color', related='company_id.snailmail_color', readonly=False)
    snailmail_cover = fields.Boolean(string='Add a Cover Page', related='company_id.snailmail_cover', readonly=False)
    snailmail_duplex = fields.Boolean(string='Print Both sides', related='company_id.snailmail_duplex', readonly=False)
