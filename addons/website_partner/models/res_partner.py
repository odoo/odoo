# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class WebsiteResPartner(osv.Model):
    _name = 'res.partner'
    _inherit = ['res.partner','website.seo.metadata']

    _columns = {
        'website_published': fields.boolean(
            'Publish', help="Publish on the website"),
        'website_description': fields.html(
            'Website Partner Full Description'
        ),
        'website_short_description': fields.text(
            'Website Partner Short Description'
        ),
    }
    _defaults = {
        'website_published': False
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])
