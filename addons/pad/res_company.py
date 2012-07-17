# -*- coding: utf-8 -*-
from osv import fields, osv

PAD_TEMPLATE = 'http://beta.etherpad.org/p/%(db).10s-%(model)s-%(salt)s'
PAD_API_KEY = 'EtherpadFTW'

class company_pad(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'pad_url_template': fields.char('Pad URL Template', size=128, required=True,
                                 help="Template used to generate pad URL."),
        'etherpad_api_key': fields.char('Pad API Key', size=128),
    }
    _defaults = {
        'pad_url_template': PAD_TEMPLATE,
        'etherpad_api_key': PAD_API_KEY,
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
