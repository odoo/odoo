# -*- coding: utf-8 -*-

import urllib

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.addons.website_partner.controllers import main as website_partner


class WebsiteCrmPartnerAssign(http.Controller):
    _references_per_page = 20

    @website.route([
        '/partners/',
        '/partners/page/<int:page>/',
        '/partners/country/<int:country_id>',
        '/partners/country/page/<int:country_id>/',
    ], type='http', auth="public", multilang=True)
    def partners(self, country_id=0, page=0, **post):
        country_obj = request.registry['res.country']
        partner_obj = request.registry['res.partner']
        post_name = post.get('search', '')
        grade_id = post.get('grade', '')
        country = None

        # format displayed membership lines domain
        base_partner_domain = [('is_company', '=', True), ('grade_id', '!=', False), ('website_published', '=', True)]
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
            request.cr, openerp.SUPERUSER_ID, partner_domain,
            context=request.context)
        pager = request.website.pager(url="/partners/", total=len(partner_ids), page=page, step=self._references_per_page, scope=7, url_args=post)

        # search for partners to display
        partners_data = partner_obj.search_read(request.cr, openerp.SUPERUSER_ID,
            domain=partner_domain,
            fields=request.website.get_partner_white_list_fields(),
            offset=pager['offset'],
            limit=self._references_per_page,
            order="grade_id DESC,partner_weight DESC",
            context=request.context)
        google_map_partner_ids = ",".join([str(p['id']) for p in partners_data])

        # group by country
        countries = partner_obj.read_group(
            request.cr, openerp.SUPERUSER_ID, base_partner_domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        countries_partners = partner_obj.search(
            request.cr, openerp.SUPERUSER_ID, base_partner_domain,
            context=request.context, count=True)
        countries.insert(0, {
            'country_id_count': countries_partners,
            'country_id': (0, _("All Countries"))
        })

        # group by grade
        grades = partner_obj.read_group(
            request.cr, openerp.SUPERUSER_ID, base_partner_domain, ["id", "grade_id"],
            groupby="grade_id", orderby="grade_id", context=request.context)
        grades_partners = partner_obj.search(
            request.cr, openerp.SUPERUSER_ID, base_partner_domain,
            context=request.context, count=True)
        grades.insert(0, {
            'grade_id_count': grades_partners,
            'grade_id': ("all", _("All Levels"))
        })

        values = {
            'countries': countries,
            'current_country_id': country_id,
            'current_country': country,
            'grades': grades,
            'grade_id': grade_id,
            'partners_data': partners_data,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'searches': post,
            'search_path': "?%s" % urllib.urlencode(post),
        }
        return request.website.render("website_crm_partner_assign.index", values)

    @website.route(['/partners/<model("res.partner"):partner>/'], type='http', auth="public", multilang=True)
    def partners_ref(self, partner, **post):
        values = website_partner.get_partner_template_value(partner)
        if not values:
            return self.partners(**post)
        values['main_object'] = values['partner']
        return request.website.render("website_crm_partner_assign.partner", values)
