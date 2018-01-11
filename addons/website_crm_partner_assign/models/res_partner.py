# -*- coding: utf-8 -*-
from openerp.osv import osv, fields

class res_partner_grade(osv.osv):
    _inherit = 'res.partner.grade'
    _columns = {
        'website_published': fields.boolean('Published On Website', copy=False),
    }
