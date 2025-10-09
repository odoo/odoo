# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import http
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_google_map.controllers.main import GoogleMap
from odoo.tools.translate import LazyTranslate
from odoo.http import request
from odoo.addons.website.controllers.main import QueryURL

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

    def tags_list(self, active_tags, toggled_tag=None):
        """
        Return a comma-separated string of tag slugs for the currently active
        tags, optionally toggling the presence of a specific tag. Ensures URLs
        use slugs instead of IDs.

        :param active_tags: List or recordset of active res.partner.tag records
                            or IDs
        :param toggled_tag: Optional tag record or ID to add/remove from the
                            active list
        :return: Comma-separated string of tag slugs
        """
        Tag = request.env['res.partner.tag']

        # Convert IDs to recordset if active_tags is a list of ids
        if isinstance(active_tags, list):
            active_tags = Tag.browse(active_tags)

        tag_ids = [tag.id for tag in active_tags] if active_tags else []

        if toggled_tag:
            if isinstance(toggled_tag, int):
                toggled_tag = Tag.browse(toggled_tag)
            if toggled_tag.id in tag_ids:
                tag_ids.remove(toggled_tag.id)
            else:
                tag_ids.append(toggled_tag.id)

        return ",".join(request.env['ir.http']._slug(tag) for tag in Tag.browse(tag_ids) if tag.exists())

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

        tag_param = post.get('tag')
        active_tags = Tag.browse()
        if tag_param:
            tag_ids = []
            for slug in tag_param.split(','):
                _, tid = request.env['ir.http']._unslug(slug)
                tag_ids.append(tid)
            if tag_ids:
                active_tags = Tag.browse(tag_ids).exists()
                domain += [('website_tag_ids', 'in', active_tags.ids)]

        # group by industry, based on customers found with the search(domain)
        industry_groups = Partner.sudo()._read_group(
            domain, ["industry_id"], ["__count"], order="industry_id")

        if industry:
            domain.append(('industry_id', '=', industry.id))
            if not any(ind.id == industry.id for ind, __ in industry_groups) and industry.exists():
                industry_groups.append((industry, 0))
                industry_groups = sorted(industry_groups, key=lambda group: group[0].name or '')

        industries = [{
            'industry_id_count': sum(count for __, count, in industry_groups),
            'industry_id': (0, _lt("All Industries")),
        }]
        for g_industry, count in industry_groups:
            industries.append({
                'industry_id_count': count,
                'industry_id': g_industry and (g_industry.id, g_industry.display_name),
            })

        # group by country, based on customers found with the search(domain)
        country_groups = Partner.sudo()._read_group(domain, ["country_id"], ["__count"], order="country_id")

        fallback_all_countries = False
        if country:
            if country_groups and country.id not in (country.id for country, __ in country_groups):
                # fallback on all countries if no customer found for the country
                # and there are matching customers for other countries
                fallback_all_countries = True
                country = None
            else:
                domain += [('country_id', '=', country.id)]

        countries = [{
            'country_id_count': sum(count for __, count in country_groups),
            'country_id': (0, _lt("All Countries")),
        }]
        for g_country, count in country_groups:
            countries.append({
                'country_id_count': count,
                'country_id': g_country and (g_country.id, g_country.sudo().display_name),
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
        google_maps_api_key = request.website.google_maps_api_key

        tags = Tag.search([('website_published', '=', True), ('partner_ids', 'in', partners.ids)], order='classname, name ASC')

        values = {
            'countries': countries,
            'current_country_id': country.id if country and partners else 0,
            'current_country': country if partners and country else False,
            'industries': industries,
            'current_industry_id': industry.id if industry else 0,
            'current_industry': industry or False,
            'partners': partners,
            'pager': pager,
            'post': post,
            'search_path': "?%s" % werkzeug.urls.url_encode(post),
            'tag': active_tags,
            'tags': tags,
            'active_tag_ids': active_tags.ids,
            'tags_list': self.tags_list,
            'search': search_value,
            'search_count': partner_count,
            'google_maps_api_key': google_maps_api_key,
            'fallback_all_countries': fallback_all_countries,
        }

        values['customer_url'] = QueryURL('/customers',
            ['search', 'industry', 'country'],
            tag=self.tags_list(active_tags),
            search=search_value,
            country=country,
            industry=industry,
        )

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
