# -*- coding: utf-8 -*-
from osv import fields, osv

class company_pad(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'pad_index': fields.char('Pad root URL', size=64, required=True,
                                 help="The root URL of the company's pad "
                                      "instance"),
    }
    _defaults = {
        'pad_index': 'http://ietherpad.com/'
    }

