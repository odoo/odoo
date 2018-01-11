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
        'module_crm_profiling': fields.boolean(
            'Track customer profile to focus your campaigns',
            help='Allows users to perform segmentation within partners.\n'
                 '-This installs the module crm_profiling.'),
    }
