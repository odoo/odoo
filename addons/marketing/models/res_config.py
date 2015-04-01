# -*- coding: utf-8 -*-

from openerp import models, fields

class MarketingConfigSettings(models.TransientModel):
    _name = 'marketing.config.settings'
    _inherit = 'res.config.settings'

    module_marketing_campaign = fields.Boolean(string='Marketing campaigns',
                                               help='Provides leads automation through marketing campaigns. '
                                               'Campaigns can in fact be defined on any resource, not just CRM leads.\n'
                                               '-This installs the module marketing_campaign.')
