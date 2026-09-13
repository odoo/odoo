# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import http
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_google_map.controllers.main import GoogleMap
from odoo.tools.translate import _, LazyTranslate
from odoo.http import request

_lt = LazyTranslate(__name__)


class WebsiteCustomer(GoogleMap):
    _references_per_page = 20

    def _get_gmap_domains(self, **kw):
        if kw.get('dom', '') != "website_customer.customers":
            return super()._get_gmap_domains(**kw)

        current_industry = kw.get('current_industry')
        current_country = kw.get('current_country')

        domain = [('assigned_partner_id', '!=', False)]

        if current_country and current_country != '0':
            domain += [('country_id', '=', int(current_country))]

        if current_industry and current_industry != '0':
            domain += [('industry_id', '=', int(current_industry))]

        return domain

    def sitemap_industry(env, rule, qs):
        if not qs or qs.lower() in '/customers':
            yield {'loc': '/customers'}

        Industry = env['res.partner.industry']
        dom = sitemap_qs2dom(qs, '/customers/industry', Industry._rec_name)
        for industry in Industry.search(dom):
            loc = '/customers/industry/%s' % env['ir.http']._slug(industry)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

        dom = [('website_published', '=', True), ('assigned_partner_id', '!=', False), ('country_id', '!=', False)]
        dom += sitemap_qs2dom(qs, '/customers/country')
        countries = env['res.partner'].sudo()._read_group(dom, ['country_id'])
        for [country] in countries:
            loc = '/customers/country/%s' % env['ir.http']._slug(country)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def _get_customers_search_options(self, industry=None, country=None, **post):
        return {
            'allowFuzzy': not post.get('noFuzzy'),
            'searchType': 'customers',
            'industry': request.env['ir.http']._slug(industry) if industry else None,
            'country': request.env['ir.http']._slug(country) if country else None,
            'tag_id': post.get('tag_id')
        }

    def _get_customers(self, search, offset, limit, order, options):
        # search partners matching current search parameters
        customer_count, details, fuzzy_search_term = self.env.website._search_with_fuzzy(
            search_type='customers',
            search=search,
            offset=offset,
            limit=limit,
            order=order,
            options=options
        )
        customers = details[0].get('results')
        return customer_count, customers, fuzzy_search_term

    @http.route([
        '/customers',
        '/customers/page/<int:page>',
        '/customers/country/<model("res.country"):country>',
        '/customers/country/<model("res.country"):country>/page/<int:page>',
        '/customers/industry/<model("res.partner.industry"):industry>',
        '/customers/industry/<model("res.partner.industry"):industry>/page/<int:page>',
        '/customers/industry/<model("res.partner.industry"):industry>/country/<model("res.country"):country>',
        '/customers/industry/<model("res.partner.industry"):industry>/country/<model("res.country"):country>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_industry, list_as_website_content=_lt("Customers"))
    def customers(self, country=None, industry=None, page=1, **post):
        Tag = request.env['res.partner.tag']
        Partner = request.env['res.partner']
        search = post.get('search', "")
        tag_id = post.get('tag_id')
        if tag_id:
            tag_id = request.env['ir.http']._unslug(tag_id)[1] or 0
        order = 'is_published desc, %s, id desc' % post.get('order', "name ASC")
        search_details = self.env.website._search_get_details(
            search_type='customers',
            order=order,
            options={
                'allowFuzzy': not post.get('noFuzzy'),
                'tag_id': post.get('tag_id'),
                'searchType': 'customers',
            }
        )
        fuzzy_search_term = self.env.website._search_find_fuzzy_term(search_details, search)
        if fuzzy_search_term:
            if fuzzy_search_term.lower() == search.lower():
                fuzzy_search_term = False
        post['search'] = fuzzy_search_term or search
        final_search_domain = self.env.website._search_build_domain(
            domain_list=search_details[0].get('base_domain', []),
            search=fuzzy_search_term or search,
            fields=search_details[0].get('search_fields'),
            extra=search_details[0].get('search_extra', [])
        )

        country_domain = list(final_search_domain)
        if industry:
            country_domain += [('industry_id', '=', industry.id)]
        country_groups = Partner.sudo()._read_group(
            final_search_domain,
            ["country_id"],
            ["__count"],
            order="country_id"
        )

        countries = [{
            'country_id_count': sum(count for __, count in country_groups),
            'country_id': (0, _("All Countries")),
        }]
        for g_country, count in country_groups:
            countries.append({
                'country_id_count': count,
                'country_id': g_country and (g_country.id, g_country.sudo().display_name),
            })
        fallback_all_countries = False
        if country:
            if country_groups and country.id not in (country.id for country, __ in country_groups):
                # fallback on all countries if no customer found for the country
                # and there are matching customers for other countries
                fallback_all_countries = True
                country = None

        industry_domain = list(final_search_domain)
        if country:
            industry_domain += [('country_id', '=', country.id)]
        industry_groups = Partner.sudo()._read_group(
            industry_domain,
            ["industry_id"],
            ["__count"],
            order="industry_id"
        )

        if industry and not any(ind.id == industry.id for ind, __ in industry_groups) and industry.exists():
            industry_groups.append((industry, 0))
            industry_groups = sorted(industry_groups, key=lambda group: group[0].name or '')

        industries = [{
            'industry_id_count': sum(count for __, count, in industry_groups),
            'industry_id': (0, _("All Industries")),
        }]
        for g_industry, count in industry_groups:
            industries.append({
                'industry_id_count': count,
                'industry_id': g_industry and (g_industry.id, g_industry.display_name),
            })

        options = self._get_customers_search_options(industry=industry, country=country, **post)
        customer_count, customers, fuzzy_search_term = self._get_customers(
            search=search,
            offset=(page - 1) * self._references_per_page,
            limit=self._references_per_page,
            order=order,
            options=options
        )

        # pager
        url = '/customers'
        if industry:
            url += '/industry/%s' % industry.id
        if country:
            url += '/country/%s' % country.id
        pager = self.env.website.pager(
            url=url,
            total=customer_count,
            page=page,
            step=self._references_per_page,
            scope=7,
            url_args=post
        )

        google_maps_api_key = self.env.website.google_maps_api_key

        tags = Tag.search(
            [('website_published', '=', True), ('partner_ids', 'in', customers.ids)],
            order='classname, name ASC'
        )
        tag = tag_id and Tag.browse(tag_id) or False

        keep = QueryURL(
            '/customers',
            ['industry', 'country'],
            industry=industry,
            country=country,
            **{key: value for key, value in post.items() if (key in ['search', 'tag_id'])}
        )
        values = {
            'countries': countries,
            'current_country_id': country.id if country and customers else 0,
            'current_country': country if customers and country else False,
            'industries': industries,
            'current_industry_id': industry.id if industry else 0,
            'current_industry': industry or False,
            'partners': customers,
            'pager': pager,
            'post': post,
            'search_path': "?%s" % werkzeug.urls.url_encode(post),
            'tag': tag,
            'tags': tags,
            'google_maps_api_key': google_maps_api_key,
            'fallback_all_countries': fallback_all_countries,
            'search_count': customer_count,
            'original_search': final_search_domain or search,
            'keep_customers_url': keep,
        }
        return request.render("website_customer.index", values)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/customers/<partner_id>'], type='http', auth="public", website=True)
    def customers_detail(self, partner_id, **post):
        current_slug = partner_id
        _, partner_id = request.env['ir.http']._unslug(partner_id)
        if partner_id:
            partner = request.env['res.partner'].sudo().browse(partner_id)
            if partner.exists() and partner.website_published:
                if request.env['ir.http']._slug(partner) != current_slug:
                    return request.redirect('/customers/%s' % request.env['ir.http']._slug(partner))
                values = {}
                values['main_object'] = values['partner'] = partner
                return request.render("website_customer.details", values)
        raise request.not_found()
