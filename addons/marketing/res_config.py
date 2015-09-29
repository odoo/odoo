# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class marketing_config_settings(osv.TransientModel):
    _name = 'marketing.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'module_marketing_campaign': fields.boolean(
            'Marketing campaigns',
            help='Provides leads automation through marketing campaigns. '
                 'Campaigns can in fact be defined on any resource, not just CRM leads.\n'
                 '-This installs the module marketing_campaign.'),
    }
