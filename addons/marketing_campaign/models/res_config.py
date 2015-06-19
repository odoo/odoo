# -*- coding: utf-8 -*-

from openerp import fields, models


class MarketingCampaignConfig(models.TransientModel):
    _name = 'marketing.campaign.config.settings'
    _inherit = 'res.config.settings'

    module_marketing_campaign_crm_demo = fields.Boolean(
        string='Demo data for marketing campaigns',
        help='Installs demo data like leads, campaigns and segments for Marketing Campaigns.\n'
             '-This installs the module marketing_campaign_crm_demo.')
