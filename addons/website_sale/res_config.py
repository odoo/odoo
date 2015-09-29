# -*- encoding: utf-8 -*-
from openerp import models, fields

class website_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'

    salesperson_id = fields.Many2one('res.users', related='website_id.salesperson_id', string='Salesperson')
    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Team')
