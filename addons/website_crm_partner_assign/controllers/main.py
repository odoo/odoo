# -*- coding: utf-8 -*-

import urllib

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website.models import website


class WebsiteCrmPartnerAssign(http.Controller):
    _references_per_page = 20

    @website.route([
        '/partners/', '/partners/page/<int:page>/',
        '/partners/country/<int:country_id>', '/partners/country/page/<int:country_id>/',
    ], type='http', auth="public", multilang=True)
    def partners(self, country_id=0, page=0, **post):
        country_obj = request.registry['res.country']
        partner_obj = request.registry['res.partner']
        post_name = post.get('search', '')
        grade_id = post.get('grade', '')
        country = None

        # format displayed membership lines domain
        base_partner_domain = [('is_company', '=', True)]
        partner_domain = list(base_partner_domain)
        if grade_id and grade_id != "all":
            partner_domain += [('grade_id', '=', int(grade_id))]  # try/catch int
        if country_id:
            country = country_obj.browse(request.cr, request.uid, country_id, request.context)
            partner_domain += [('country_id', '=', country_id)]
        if post_name:
            partner_domain += ['|', ('name', 'ilike', "%%%s%%" % post_name), ('website_description', 'ilike', "%%%s%%" % post_name)]

        # format pager
        partner_ids = partner_obj.search(
            request.cr, request.uid, partner_domain,
            context=request.context)
        pager = request.website.pager(url="/partners/", total=len(partner_ids), page=page, step=self._references_per_page, scope=7, url_args=post)

        # search for partners to display
        partner_ids = partner_obj.search(
            request.cr, request.uid, partner_domain,
            context=request.context,
            limit=self._references_per_page, offset=pager['offset'],
            order="grade_id ASC,partner_weight DESC")
        google_map_partner_ids = ",".join([str(p) for p in partner_ids])
        partners = partner_obj.browse(
            request.cr, request.uid, partner_ids, request.context)

        # group by country
        countries = partner_obj.read_group(
            request.cr, request.uid, base_partner_domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        countries_partners = partner_obj.search(
            request.cr, request.uid, base_partner_domain,
            context=request.context, count=True)
        countries.insert(0, {
            'country_id_count': countries_partners,
            'country_id': (0, _("All Countries"))
        })

        # group by grade
        grades = partner_obj.read_group(
            request.cr, request.uid, base_partner_domain, ["id", "grade_id"],
            groupby="grade_id", orderby="grade_id", context=request.context)
        grades_partners = partner_obj.search(
            request.cr, request.uid, base_partner_domain,
            context=request.context, count=True)
        grades.insert(0, {
            'grade_id_count': grades_partners,
            'grade_id': ("all", _("All Grades"))
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
            'search_path': "?%s" % urllib.urlencode(post),
        }
        return request.website.render("website_crm_partner_assign.index", values)

    @website.route(['/partners/<int:partner_id>/'], type='http', auth="public", multilang=True)
    def partners_ref(self, partner_id=0, **post):
        partner_obj = request.registry['res.partner']
        partner_ids = partner_obj.search(request.cr, request.uid, [('id', '=', partner_id)], context=request.context)
        if not partner_ids:
            return self.members(post)

        values = {
            'partner_id': partner_obj.browse(
                request.cr, request.uid, partner_ids[0],
                context=dict(request.context, show_address=True)),
        }
        return request.website.render("website_crm_partner_assign.partner", values)
