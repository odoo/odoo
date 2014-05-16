# -*- coding: utf-8 -*-
import re

import werkzeug

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug
from openerp.tools.translate import _


class WebsiteCrmPartnerAssign(http.Controller):
    _references_per_page = 40

    @http.route([
        '/partners',
        '/partners/page/<int:page>',

        '/partners/grade/<model("res.partner.grade"):grade>',
        '/partners/grade/<model("res.partner.grade"):grade>/page/<int:page>',

        '/partners/country/<model("res.country"):country>',
        '/partners/country/<model("res.country"):country>/page/<int:page>',

        '/partners/grade/<model("res.partner.grade"):grade>/country/<model("res.country"):country>',
        '/partners/grade/<model("res.partner.grade"):grade>/country/<model("res.country"):country>/page/<int:page>',
    ], type='http', auth="public", website=True, multilang=True)
    def partners(self, country=None, grade=None, page=0, **post):
        partner_obj = request.registry['res.partner']
        search = post.get('search', '')

        base_partner_domain = [('is_company', '=', True), ('grade_id.website_published', '=', True), ('website_published', '=', True)]
        if search:
            base_partner_domain += ['|', ('name', 'ilike', search), ('website_description', 'ilike', search)]

        # group by grade
        grade_domain = list(base_partner_domain)
        if country:
            grade_domain += [('country_id', '=', country.id)]
        grades = partner_obj.read_group(
            request.cr, SUPERUSER_ID, grade_domain, ["id", "grade_id"],
            groupby="grade_id", orderby="grade_id DESC", context=request.context)
        grades_partners = partner_obj.search(
            request.cr, SUPERUSER_ID, grade_domain,
            context=request.context, count=True)
        # flag active grade
        for grade_dict in grades:
            grade_dict['active'] = grade and grade_dict['grade_id'][0] == grade.id
        grades.insert(0, {
            'grade_id_count': grades_partners,
            'grade_id': (0, _("All Categories")),
            'active': bool(grade is None),
        })

        # group by country
        country_domain = list(base_partner_domain)
        if grade:
            country_domain += [('grade_id', '=', grade.id)]
        countries = partner_obj.read_group(
            request.cr, SUPERUSER_ID, country_domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        countries_partners = partner_obj.search(
            request.cr, SUPERUSER_ID, country_domain,
            context=request.context, count=True)
        # flag active country
        for country_dict in countries:
            country_dict['active'] = country and country_dict['country_id'][0] == country.id
        countries.insert(0, {
            'country_id_count': countries_partners,
            'country_id': (0, _("All Countries")),
            'active': bool(country is None),
        })

        # current search
        if grade:
            base_partner_domain += [('grade_id', '=', grade.id)]
        if country:
            base_partner_domain += [('country_id', '=', country.id)]

        # format pager
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
        partner_count = partner_obj.search_count(
            request.cr, SUPERUSER_ID, base_partner_domain,
            context=request.context)
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=self._references_per_page, scope=7,
            url_args=url_args)

        # search partners matching current search parameters
        partner_ids = partner_obj.search(
            request.cr, SUPERUSER_ID, base_partner_domain,
            offset=pager['offset'], limit=self._references_per_page,
            order="grade_id DESC, implemented_count DESC",
            context=request.context)
        google_map_partner_ids = ','.join(map(str, partner_ids))
        partners = partner_obj.browse(request.cr, SUPERUSER_ID, partner_ids, request.context)

        values = {
            'countries': countries,
            'current_country': country,
            'grades': grades,
            'current_grade': grade,
            'partners': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'searches': post,
            'search_path': "?%s" % werkzeug.url_encode(post),
        }
        return request.website.render("website_crm_partner_assign.index", values)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/partners/<partner_id>'], type='http', auth="public", website=True, multilang=True)
    def partners_detail(self, partner_id, partner_name='', **post):
        mo = re.search('-([-0-9]+)$', str(partner_id))
        if mo:
            partner_id = int(mo.group(1))
            partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_id, context=request.context)
            if partner.exists() and partner.website_published:
                values = {}
                values['main_object'] = values['partner'] = partner
                return request.website.render("website_crm_partner_assign.partner", values)
        return self.partners(**post)
