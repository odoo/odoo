# -*- coding: utf-8 -*-
import re

import werkzeug

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.translate import _

class WebsiteCrmPartnerAssign(http.Controller):
    _references_per_page = 20

    @http.route([
        '/partners',
        '/partners/page/<int:page>',

        '/partners/grade/<int:grade_id>',
        '/partners/grade/<int:grade_id>/page/<int:page>',

        '/partners/country/<int:country_id>',
        '/partners/country/<country_name>-<int:country_id>',
        '/partners/country/<int:country_id>/page/<int:page>',
        '/partners/country/<country_name>-<int:country_id>/page/<int:page>',

        '/partners/grade/<int:grade_id>/country/<int:country_id>',
        '/partners/grade/<int:grade_id>/country/<country_name>-<int:country_id>',
        '/partners/grade/<int:grade_id>/country/<int:country_id>/page/<int:page>',
        '/partners/grade/<int:grade_id>/country/<country_name>-<int:country_id>/page/<int:page>',

    ], type='http', auth="public", website=True, multilang=True)
    def partners(self, country_id=0, grade_id=0, page=0, country_name='', **post):
        country_obj = request.registry['res.country']
        partner_obj = request.registry['res.partner']
        post_name = post.get('search', '')
        country = None

        # format displayed membership lines domain
        base_partner_domain = [('is_company', '=', True), ('grade_id.website_published', '=', True), ('website_published', '=', True)]
        partner_domain = list(base_partner_domain)
        if post_name:
            partner_domain += ['|', ('name', 'ilike', post_name), ('website_description', 'ilike', post_name)]
        if grade_id and grade_id != "all":
            partner_domain += [('grade_id', '=', int(grade_id))]  # try/catch int

        # group by country
        countries = partner_obj.read_group(
            request.cr, SUPERUSER_ID, partner_domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        countries_partners = partner_obj.search(
            request.cr, SUPERUSER_ID, partner_domain,
            context=request.context, count=True)

        if country_id:
            country = country_obj.browse(request.cr, request.uid, country_id, request.context)
            partner_domain += [('country_id', '=', country_id)]
            if not any(x['country_id'][0] == country_id for x in countries):
                countries.append({
                    'country_id_count': 0,
                    'country_id': (country_id, country.name)
                })
                countries.sort(key=lambda d: d['country_id'][1])

        countries.insert(0, {
            'country_id_count': countries_partners,
            'country_id': (0, _("All Countries"))
        })

        # format pager
        partner_count = partner_obj.search_count(
            request.cr, SUPERUSER_ID, partner_domain,
            context=request.context)
        pager = request.website.pager(url="/partners", total=partner_count, page=page, step=self._references_per_page, scope=7, url_args=post)

        partner_ids = partner_obj.search(request.cr, SUPERUSER_ID, partner_domain,
                                         offset=pager['offset'], limit=self._references_per_page,
                                         order="grade_id DESC, partner_weight DESC",
                                         context=request.context)
        google_map_partner_ids = ','.join(map(str, partner_ids))
        partners = partner_obj.browse(request.cr, SUPERUSER_ID, partner_ids, request.context)

        # group by grade
        grades = partner_obj.read_group(
            request.cr, SUPERUSER_ID, base_partner_domain, ["id", "grade_id"],
            groupby="grade_id", orderby="grade_id DESC", context=request.context)
        grades_partners = partner_obj.search(
            request.cr, SUPERUSER_ID, base_partner_domain,
            context=request.context, count=True)
        grades.insert(0, {
            'grade_id_count': grades_partners,
            'grade_id': (0, _("All Categories"))
        })

        values = {
            'countries': countries,
            'current_country_id': country_id,
            'current_country': country,
            'grades': grades,
            'grade_id': grade_id,
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
