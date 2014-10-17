# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class WebsiteResPartner(osv.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata']

    def _get_ids(self, cr, uid, ids, flds, args, context=None):
        return {i: i for i in ids}

    def _set_private(self, cr, uid, ids, field_name, value, arg, context=None):
        return self.write(cr, uid, ids, {'website_published': not value}, context=context)

    def _get_private(self, cr, uid, ids, field_name, arg, context=None):
        return dict((rec.id, not rec.website_published) for rec in self.browse(cr, uid, ids, context=context))

    def _search_private(self, cr, uid, obj, name, args, context=None):
        return [('website_published', '=', not args[0][2])]

    _columns = {
        'website_published': fields.boolean(
            'Publish', help="Publish on the website", copy=False),
        'website_private': fields.function(
            _get_private, fnct_inv=_set_private, fnct_search=_search_private,
            type='boolean', string='Private Profile'),
        'website_description': fields.html(
            'Website Partner Full Description'
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
