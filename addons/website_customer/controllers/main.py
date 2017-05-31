# -*- coding: utf-8 -*-
import openerp
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.website.models.website import unslug
from openerp.tools.translate import _
from openerp.addons.web.http import request
import werkzeug.urls


class WebsiteCustomer(http.Controller):
    _references_per_page = 20

    @http.route([
        '/customers',
        '/customers/page/<int:page>',
        '/customers/country/<int:country_id>',
        '/customers/country/<country_name>-<int:country_id>',
        '/customers/country/<int:country_id>/page/<int:page>',
        '/customers/country/<country_name>-<int:country_id>/page/<int:page>',
        '/customers/tag/<tag_id>',
        '/customers/tag/<tag_id>/page/<int:page>',
        '/customers/tag/<tag_id>/country/<int:country_id>',
        '/customers/tag/<tag_id>/country/<country_name>-<int:country_id>',
        '/customers/tag/<tag_id>/country/<int:country_id>/page/<int:page>',
        '/customers/tag/<tag_id>/country/<country_name>-<int:country_id>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def customers(self, country_id=0, page=0, country_name='', tag_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        country_obj = request.registry['res.country']
        tag_obj = request.registry['res.partner.tag']
        partner_obj = request.registry['res.partner']
        partner_name = post.get('search', '')

        domain = [('website_published', '=', True), ('assigned_partner_id', '!=', False)]
        if partner_name:
            domain += [
                '|',
                ('name', 'ilike', post.get("search")),
                ('website_description', 'ilike', post.get("search"))
            ]

        if tag_id:
            tag_id = unslug(tag_id)[1] or 0
            domain += [('website_tag_ids', 'in', tag_id)]

        # group by country, based on customers found with the search(domain)
        countries = partner_obj.read_group(
            cr, openerp.SUPERUSER_ID, domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        country_count = partner_obj.search(
            cr, openerp.SUPERUSER_ID, domain, count=True, context=request.context)

        if country_id:
            domain += [('country_id', '=', country_id)]
            if not any(x['country_id'][0] == country_id for x in countries if x['country_id']):
                country = country_obj.read(cr, uid, country_id, ['name'], context)
                if country:
                    countries.append({
                        'country_id_count': 0,
                        'country_id': (country_id, country['name'])
                    })
                countries.sort(key=lambda d: d['country_id'] and d['country_id'][1])
            curr_country = country_obj.browse(cr, uid, country_id, context)

        countries.insert(0, {
            'country_id_count': country_count,
            'country_id': (0, _("All Countries"))
        })

        # search customers to display
        partner_count = partner_obj.search_count(cr, openerp.SUPERUSER_ID, domain, context=request.context)

        # pager
        url = '/customers'
        if country_id:
            url += '/country/%s' % country_id
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=self._references_per_page,
            scope=7, url_args=post
        )

        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, domain,
                                         offset=pager['offset'], limit=self._references_per_page,
                                         context=request.context)
        google_map_partner_ids = ','.join(map(str, partner_ids))
        partners = partner_obj.browse(request.cr, openerp.SUPERUSER_ID, partner_ids, request.context)
        google_maps_api_key = request.env['ir.config_parameter'].sudo().get_param('google_maps_api_key')

        tag_obj = request.registry['res.partner.tag']
        tag_ids = tag_obj.search(cr, uid, [('website_published', '=', True), ('partner_ids', 'in', partner_ids)],
                                 order='classname, name ASC', context=context)
        tags = tag_obj.browse(cr, uid, tag_ids, context=context)
        tag = tag_id and tag_obj.browse(cr, uid, tag_id, context=context) or False

        values = {
            'countries': countries,
            'current_country_id': country_id or 0,
            'current_country': country_id and curr_country or False,
            'partners': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'post': post,
            'search_path': "?%s" % werkzeug.url_encode(post),
            'tag': tag,
            'tags': tags,
            'google_maps_api_key': google_maps_api_key,
        }
        return request.website.render("website_customer.index", values)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/customers/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        _, partner_id = unslug(partner_id)
        if partner_id:
            partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_id, context=request.context)
            if partner.exists() and partner.website_published:
                values = {}
                values['main_object'] = values['partner'] = partner
                return request.website.render("website_customer.details", values)
        return self.customers(**post)
