# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class MarketingCampaignConfig(osv.TransientModel):
    _name = 'marketing.campaign.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_marketing_campaign_crm_demo': fields.boolean(
            'Demo data for marketing campaigns',
            help='Installs demo data like leads, campaigns and segments for Marketing Campaigns.\n'
                 '-This installs the module marketing_campaign_crm_demo.'),
    }