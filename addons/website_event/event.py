# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class event(osv.osv):
    _inherit = 'event.event'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
    }

