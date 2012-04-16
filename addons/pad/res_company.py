# -*- coding: utf-8 -*-
from osv import fields, osv

class company_pad(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'pad_url_template': fields.char('Pad URL Template', size=128, required=True,
                                 help="Template used to generate pad URL."),
    }
    _defaults = {
        'pad_url_template': 'http://beta.etherpad.org/p/%(db)s-%(model)s-%(id)d-%(salt)s-%(name)s'
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
