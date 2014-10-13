# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class CrmMarketingConfig(osv.TransientModel):
    _name = 'marketing.config.settings'
    _inherit = 'marketing.config.settings'

    _columns = {
        'module_marketing_campaign_crm_demo': fields.boolean(
            'Demo data for marketing campaigns',
            help='Installs demo data like leads, campaigns and segments for Marketing Campaigns.\n'
                 '-This installs the module marketing_campaign_crm_demo.'),
    }
