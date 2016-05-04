from odoo import fields, models

class Website(models.Model):
    _inherit = 'website'

    salesteam_id = fields.Many2one('crm.team', string='Sales Team')

class WebsiteConfigSettings(models.TransientModel):
    _inherit = 'website.config.settings'

    salesteam_id = fields.Many2one('crm.team', related='website_id.salesteam_id', string='Sales Team')
