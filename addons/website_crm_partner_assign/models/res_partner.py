# -*- coding: utf-8 -*-

from openerp.osv import osv, fields

class res_partner_grade(osv.osv):
    _inherit = 'res.partner.grade'
    _columns = {
        'website_description': fields.html('Description for the website'),
    }

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = ['res.partner','website.seo.metadata']