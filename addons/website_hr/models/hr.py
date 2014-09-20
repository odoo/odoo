# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr(osv.osv):
    _inherit = 'hr.employee'
    _columns = {
        'website_published': fields.boolean('Available in the website', copy=False),
        'public_info': fields.text('Public Info'),
    }
    _defaults = {
        'website_published': False
    }
