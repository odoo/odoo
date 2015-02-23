# -*- coding: utf-8 -*-

import werkzeug
from openerp import http, _
from openerp.http import request
from openerp.addons.website.models.website import slug, unslug
from openerp.addons.website_partner.controllers.main import WebsitePartnerPage


class WebsiteCrmPartnerAssign(WebsitePartnerPage):
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
    ], type='http', auth="public", website=True)
    def partners(self, country=None, grade=None, page=0, **post):
        country_all = post.pop('country_all', False)
        PartnerSudo = request.env['res.partner'].sudo()
        search = post.get('search', '')
        grade_count, country_count = 0, 0

        base_partner_domain = [('is_company', '=', True), ('grade_id', '!=', False), ('website_published', '=', True)]
        if not request.env['res.users'].has_group('base.group_website_publisher'):
            base_partner_domain += [('grade_id.website_published', '=', True)]
        if search:
            base_partner_domain += ['|', ('name', 'ilike', search), ('website_description', 'ilike', search)]

        # group by grade
        grade_domain = list(base_partner_domain)
        if not country and not country_all:
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country = request.env['res.country'].search([('code', '=', country_code)], limit=1)
        if country:
            grade_domain += [('country_id', '=', country.id)]
        grades = PartnerSudo.read_group(grade_domain, ["id", "grade_id"], groupby="grade_id", orderby="grade_id DESC")
        # flag active grade
        for grade_dict in grades:
            grade_dict['active'] = grade and grade_dict['grade_id'][0] == grade.id
            grade_count += grade_dict['grade_id_count']
        grades.insert(0, {
            'grade_id_count': grade_count,
            'grade_id': (0, _("All Categories")),
            'active': bool(grade is None),
        })

        # group by country
        country_domain = list(base_partner_domain)
        if grade:
            country_domain += [('grade_id', '=', grade.id)]
        countries = PartnerSudo.read_group(country_domain, ["id", "country_id"], groupby="country_id", orderby="country_id")
        # flag active country
        for country_dict in countries:
            country_dict['active'] = country and country_dict['country_id'] and country_dict['country_id'][0] == country.id
            country_count += country_dict['country_id_count']
        countries.insert(0, {
            'country_id_count': country_count,
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
        if country_all:
            url_args['country_all'] = True

        partner_count = PartnerSudo.search_count(base_partner_domain)
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=self._references_per_page, scope=7,
            url_args=url_args)

        # search partners matching current search parameters
        partners = PartnerSudo.search(base_partner_domain, order="grade_id DESC")  # todo in trunk: order="grade_id DESC, implemented_count DESC", offset=pager['offset'], limit=self._references_per_page
        # remove me in trunk
        partners = sorted(partners, key=lambda x: (x.grade_id.sequence if x.grade_id else 0, len([i for i in x.implemented_partner_ids if i.website_published])), reverse=True)
        partners = partners[pager['offset']:pager['offset'] + self._references_per_page]

        google_map_partner_ids = ','.join(map(str, [p.id for p in partners]))

        values = {
            'countries': countries,
            'current_country': country,
            'grades': grades,
            'current_grade': grade,
            'partners': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'searches': post,
            'search_path': "%s" % werkzeug.url_encode(post),
        }
        return request.website.render("website_crm_partner_assign.index", values)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/partners/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        _, partner_id = unslug(partner_id)
        grade_id = post.get('grade_id')
        country_id = post.get('country_id')
        partner_sudo = request.env['res.partner'].sudo().browse(partner_id)
        is_website_publisher = request.env['res.users'].has_group('base.group_website_publisher')
        if partner_sudo.exists() and (partner_sudo.website_published or is_website_publisher):
            values = dict(main_object=partner_sudo, partner=partner_sudo, current_grade=None, current_country=None)
            if grade_id:
                values['current_grade'] = request.env['res.partner.grade'].browse(int(grade_id)).exists()
            if country_id:
                values['current_country'] = request.env['res.country'].browse(int(country_id)).exists()
            return request.website.render("website_crm_partner_assign.partner", values)
        return self.partners(**post)
