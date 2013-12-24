# -*- coding: utf-8 -*-
from openerp.osv import orm


class Website(orm.Model):
    _inherit = 'website'

    def get_partner_white_list_fields(self, cr, uid, ids, context=None):
        return ["name", "parent_id", 'website_short_description', "website_published", 
            "website_description", "tel", "fax", "image", "image_small", "image_medium"]