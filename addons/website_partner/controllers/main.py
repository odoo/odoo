# -*- coding: utf-8 -*-

import werkzeug.urls

from odoo import http
from odoo.http import request

from odoo.tools.translate import _


class WebsitePartnerPage(http.Controller):
    _references_per_page = 40

    def sitemap_partners(env, rule, qs):
        if not qs or qs.lower() in '/partners':
            yield {'loc': '/partners'}

        slug = env['ir.http']._slug
        base_partner_domain = [('website_published', '=', True)]
        grades = env['res.partner'].sudo()._read_group(base_partner_domain, groupby=['grade_id'])
        for [grade] in grades:
            loc = '/partners/grade/%s' % slug(grade)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}
        country_partner_domain = base_partner_domain + [('country_id', '!=', False)]
        countries = env['res.partner'].sudo()._read_group(country_partner_domain, groupby=['country_id'])
        for [country] in countries:
            loc = '/partners/country/%s' % slug(country)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def _get_partners_values(self, country=None, grade=None, page=0, references_per_page=20, **post):
        country_all = post.pop('country_all', False)
        partner_obj = request.env['res.partner']
        country_obj = request.env['res.country']

        industries = request.env['res.partner.industry'].sudo().search([])
        industry_param = request.env['ir.http']._unslug(post.pop('industry', ''))[1]
        current_industry = industry_param in industries.ids and industries.browse(int(industry_param))

        search = post.get('search', '')

        base_partner_domain = [('website_published', '=', True)]
        if search:
            base_partner_domain += ['|', ('name', 'ilike', search), ('website_description', 'ilike', search)]

        # Infer Country
        if not country and not country_all:
            if request.geoip.country_code:
                country = country_obj.search([('code', '=', request.geoip.country_code)], limit=1)

        # Group by country
        country_domain = list(base_partner_domain)
        if grade:
            country_domain += [('grade_id', '=', grade.id)]

        country_groups = partner_obj.sudo()._read_group(
            country_domain + [('country_id', '!=', False)],
            ["country_id"], ["__count"], order="country_id")

        # Fallback on all countries if no partners found for the country and
        # there are matching partners for other countries.
        fallback_all_countries = country and country.id not in (c.id for c, __ in country_groups)
        if fallback_all_countries:
            country = None

        # Group by grade
        grade_domain = list(base_partner_domain)
        if country:
            grade_domain += [('country_id', '=', country.id)]
        grade_groups = partner_obj.sudo()._read_group(
            grade_domain, ["grade_id"], ["__count"], order="grade_id")
        grades = [{
            'grade_id_count': sum(count for __, count in grade_groups),
            'grade_id': (0, ""),
            'active': grade is None,
        }]
        for g_grade, count in grade_groups:
            if g_grade:
                grades.append({
                    'grade_id_count': count,
                    'grade_id': (g_grade.id, g_grade.display_name),
                    'active': grade and grade.id == g_grade.id,
                })

        countries = [{
            'country_id_count': sum(count for __, count in country_groups),
            'country_id': (0, _("All Countries")),
            'active': country is None,
        }]
        for g_country, count in country_groups:
            countries.append({
                'country_id_count': count,
                'country_id': (g_country.id, g_country.display_name),
                'active': country and g_country.id == country.id,
            })

        # current search
        if grade:
            base_partner_domain += [('grade_id', '=', grade.id)]
        if country:
            base_partner_domain += [('country_id', '=', country.id)]
        if current_industry:
            base_partner_domain += [('implemented_partner_ids.industry_id', 'in', current_industry.id)]

        # format pager
        slug = request.env['ir.http']._slug
        if grade and not country:
            url = '/partners/grade/' + slug(grade)
        elif country and not grade:
            url = '/partners/country/' + slug(country)
        elif country and grade:
            url = '/partners/grade/' + slug(grade) + '/country/' + slug(country)
        else:
            url = '/partners'
        url_args = {}
        if search:
            url_args['search'] = search
        if country_all:
            url_args['country_all'] = True
        if current_industry:
            url_args['industry'] = slug(current_industry)

        partner_count = partner_obj.sudo().search_count(base_partner_domain)
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=references_per_page, scope=7,
            url_args=url_args)

        # search partners matching current search parameters
        partner_ids = partner_obj.sudo().search(
            base_partner_domain, order="complete_name ASC, id ASC",
            offset=pager['offset'], limit=references_per_page)
        partners = partner_ids.sudo()

        google_maps_api_key = request.website.google_maps_api_key

        values = {
            'industries': industries,
            'current_industry': current_industry,
            'countries': countries,
            'country_all': country_all,
            'current_country': country,
            'grades': grades,
            'current_grade': grade,
            'partners': partners,
            'pager': pager,
            'searches': post,
            'search_path': "%s" % werkzeug.urls.url_encode(post),
            'search': search,
            'google_maps_api_key': google_maps_api_key,
            'fallback_all_countries': fallback_all_countries,
        }
        return values

    @http.route([
        '/partners',
        '/partners/page/<int:page>',

        '/partners/grade/<model("res.partner.grade"):grade>',
        '/partners/grade/<model("res.partner.grade"):grade>/page/<int:page>',

        '/partners/country/<model("res.country"):country>',
        '/partners/country/<model("res.country"):country>/page/<int:page>',

        '/partners/grade/<model("res.partner.grade"):grade>/country/<model("res.country"):country>',
        '/partners/grade/<model("res.partner.grade"):grade>/country/<model("res.country"):country>/page/<int:page>',
        ], type='http', auth="public", website=True, sitemap=sitemap_partners, readonly=True)
    def partners(self, country=None, grade=None, sitemap=sitemap_partners, page=0, **post):
        values = self._get_partners_values(
            country=country,
            grade=grade,
            page=page,
            references_per_page=self._references_per_page,
            **post
        )
        return request.render("website_partner.index", values, status=values.get('partners') and 200 or 404)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/partners/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        current_slug = partner_id
        _, partner_id = request.env['ir.http']._unslug(partner_id)
        current_country = None
        country_id = post.get('country_id')
        if country_id:
            current_country = request.env['res.country'].browse(int(country_id)).exists()
        if partner_id:
            partner_sudo = request.env['res.partner'].sudo().browse(partner_id)
            is_website_restricted_editor = request.env.user.has_group('website.group_website_restricted_editor')
            if partner_sudo.exists() and (partner_sudo.website_published or is_website_restricted_editor):
                partner_slug = request.env['ir.http']._slug(partner_sudo)
                if partner_slug != current_slug:
                    return request.redirect('/partners/%s' % partner_slug)
                values = {
                    # See REVIEW_CAN_PUBLISH_UNSUDO
                    'main_object': partner_sudo.with_context(can_publish_unsudo_main_object=True),
                    'partner': partner_sudo,
                    'edit_page': False,
                    'current_country': current_country,
                }
                return request.render("website_partner.partner_page", values)
        raise request.not_found()
