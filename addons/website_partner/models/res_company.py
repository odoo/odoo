# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class WebsiteResCompany(osv.Model):
    _inherit = 'res.company'
    _columns = {
        'website_published': fields.related('partner_id', 'website_published', string='Publish', help="Publish on the website"),
    }
