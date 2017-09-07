# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import http
from odoo.addons.website.models.website import unslug
from odoo.tools.translate import _
from odoo.http import request


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
        Country = request.env['res.country']
        Tag = request.env['res.partner.tag']
        Partner = request.env['res.partner']
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
        countries = Partner.sudo().read_group(domain, ["id", "country_id"], groupby="country_id", orderby="country_id")
        country_count = Partner.sudo().search_count(domain)

        if country_id:
            domain += [('country_id', '=', country_id)]
            curr_country = Country.browse(country_id)
            if country_id not in (x['country_id'][0] for x in countries if x['country_id']):
                if curr_country.exists():
                    countries.append({
                        'country_id_count': 0,
                        'country_id': (curr_country.id, curr_country.name)
                    })
                countries.sort(key=lambda d: d['country_id'] and d['country_id'][1])

        countries.insert(0, {
            'country_id_count': country_count,
            'country_id': (0, _("All Countries"))
        })

        # search customers to display
        partner_count = Partner.sudo().search_count(domain)

        # pager
        url = '/customers'
        if country_id:
            url += '/country/%s' % country_id
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=self._references_per_page,
            scope=7, url_args=post
        )

        partners = Partner.sudo().search(domain, offset=pager['offset'], limit=self._references_per_page)
        google_map_partner_ids = ','.join(map(str, partners.ids))
        google_maps_api_key = request.env['ir.config_parameter'].sudo().get_param('google_maps_api_key')

        tags = Tag.search([('website_published', '=', True), ('partner_ids', 'in', partners.ids)], order='classname, name ASC')
        tag = tag_id and Tag.browse(tag_id) or False

        values = {
            'countries': countries,
            'current_country_id': country_id or 0,
            'current_country': curr_country if country_id else False,
            'partners': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'post': post,
            'search_path': "?%s" % werkzeug.url_encode(post),
            'tag': tag,
            'tags': tags,
            'google_maps_api_key': google_maps_api_key,
        }
        return request.render("website_customer.index", values)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/customers/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        _, partner_id = unslug(partner_id)
        if partner_id:
            partner = request.env['res.partner'].sudo().browse(partner_id)
            if partner.exists() and partner.website_published:
                values = {}
                values['main_object'] = values['partner'] = partner
                return request.render("website_customer.details", values)
        return self.customers(**post)
