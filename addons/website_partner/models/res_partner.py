# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class WebsiteResPartner(osv.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata']

    def _get_ids(self, cr, uid, ids, flds, args, context=None):
        return {i: i for i in ids}

    _columns = {
        'website_published': fields.boolean(
            'Publish', help="Publish on the website", copy=False),
        'website_description': fields.html(
            'Website Partner Full Description',
            strip_style=True
        ),
        'website_short_description': fields.text(
            'Website Partner Short Description'
        ),
        # hack to allow using plain browse record in qweb views
        'self': fields.function(_get_ids, type='many2one', relation=_name),
    }

    _defaults = {
        'website_published': True
    }
