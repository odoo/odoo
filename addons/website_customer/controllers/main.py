# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import http
from odoo.addons.http_routing.models.ir_http import unslug, slug
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.tools.translate import _
from odoo.http import request


class WebsiteCustomer(http.Controller):
    _references_per_page = 20

    def sitemap_industry(env, rule, qs):
        if not qs or qs.lower() in '/customers':
            yield {'loc': '/customers'}

        Industry = env['res.partner.industry']
        dom = sitemap_qs2dom(qs, '/customers/industry', Industry._rec_name)
        for industry in Industry.search(dom):
            loc = '/customers/industry/%s' % slug(industry)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

        dom = [('website_published', '=', True), ('assigned_partner_id', '!=', False), ('country_id', '!=', False)]
        dom += sitemap_qs2dom(qs, '/customers/country')
        countries = env['res.partner'].sudo().read_group(dom, ['id', 'country_id'], groupby='country_id')
        for country in countries:
            loc = '/customers/country/%s' % slug(country['country_id'])
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    @http.route([
        '/customers',
        '/customers/page/<int:page>',
        '/customers/country/<model("res.country"):country>',
        '/customers/country/<model("res.country"):country>/page/<int:page>',
        '/customers/industry/<model("res.partner.industry"):industry>',
        '/customers/industry/<model("res.partner.industry"):industry>/page/<int:page>',
        '/customers/industry/<model("res.partner.industry"):industry>/country/<model("res.country"):country>',
        '/customers/industry/<model("res.partner.industry"):industry>/country/<model("res.country"):country>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_industry)
    def customers(self, country=None, industry=None, page=0, **post):
        Tag = request.env['res.partner.tag']
        Partner = request.env['res.partner']
        search_value = post.get('search')

        domain = [('website_published', '=', True), ('assigned_partner_id', '!=', False)]
        if search_value:
            domain += [
                '|', '|',
                ('name', 'ilike', search_value),
                ('website_description', 'ilike', search_value),
                ('industry_id.name', 'ilike', search_value),
            ]

        tag_id = post.get('tag_id')
        if tag_id:
            tag_id = unslug(tag_id)[1] or 0
            domain += [('website_tag_ids', 'in', tag_id)]

        # group by industry, based on customers found with the search(domain)
        industries = Partner.sudo().read_group(domain, ["id", "industry_id"], groupby="industry_id", orderby="industry_id")
        partners_count = Partner.sudo().search_count(domain)

        if industry:
            domain.append(('industry_id', '=', industry.id))
            if industry.id not in (x['industry_id'][0] for x in industries if x['industry_id']):
                if industry.exists():
                    industries.append({
                        'industry_id_count': 0,
                        'industry_id': (industry.id, industry.name)
                    })

        industries.sort(key=lambda d: (d.get('industry_id') or (0, ''))[1])

        industries.insert(0, {
            'industry_id_count': partners_count,
            'industry_id': (0, _("All Industries"))
        })

        # group by country, based on customers found with the search(domain)
        countries = Partner.sudo().read_group(domain, ["id", "country_id"], groupby="country_id", orderby="country_id")
        country_count = Partner.sudo().search_count(domain)

        if country:
            domain += [('country_id', '=', country.id)]
            if country.id not in (x['country_id'][0] for x in countries if x['country_id']):
                if country.exists():
                    countries.append({
                        'country_id_count': 0,
                        'country_id': (country.id, country.name)
                    })
                    countries.sort(key=lambda d: (d['country_id'] or (0, ""))[1])

        countries.insert(0, {
            'country_id_count': country_count,
            'country_id': (0, _("All Countries"))
        })

        # search customers to display
        partner_count = Partner.sudo().search_count(domain)

        # pager
        url = '/customers'
        if industry:
            url += '/industry/%s' % industry.id
        if country:
            url += '/country/%s' % country.id
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=self._references_per_page,
            scope=7, url_args=post
        )

        partners = Partner.sudo().search(domain, offset=pager['offset'], limit=self._references_per_page)
        google_map_partner_ids = ','.join(str(it) for it in partners.ids)
        google_maps_api_key = request.website.google_maps_api_key

        tags = Tag.search([('website_published', '=', True), ('partner_ids', 'in', partners.ids)], order='classname, name ASC')
        tag = tag_id and Tag.browse(tag_id) or False

        values = {
            'countries': countries,
            'current_country_id': country.id if country else 0,
            'current_country': country or False,
            'industries': industries,
            'current_industry_id': industry.id if industry else 0,
            'current_industry': industry or False,
            'partners': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'post': post,
            'search_path': "?%s" % werkzeug.urls.url_encode(post),
            'tag': tag,
            'tags': tags,
            'google_maps_api_key': google_maps_api_key,
        }
        return request.render("website_customer.index", values)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/customers/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        current_slug = partner_id
        _, partner_id = unslug(partner_id)
        if partner_id:
            partner = request.env['res.partner'].sudo().browse(partner_id)
            if partner.exists() and partner.website_published:
                if slug(partner) != current_slug:
                    return request.redirect('/customers/%s' % slug(partner))
                values = {}
                values['main_object'] = values['partner'] = partner
                return request.render("website_customer.details", values)
        raise request.not_found()
