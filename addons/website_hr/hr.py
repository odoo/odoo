# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr(osv.osv):
    _inherit = 'hr.employee'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_published_on_contact_form': fields.boolean('Publish', help="Publish also on contact form"),
    }

