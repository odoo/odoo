# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website import website
import urllib

class website_crm_partner_assign(http.Controller):

    @website.route(['/partners/', '/partners/page/<int:page>/'], type='http', auth="public")
    def partners(self, page=0, **post):
        partner_obj = request.registry['res.partner']

        def dom_without(without):
            domain = [('grade_id', '!=', False)]
            domain += openerp.SUPERUSER_ID != request.uid and [('website_published', '=', True)] or [(1, "=", 1)]
            for key, search in domain_search.items():
                if key != without:
                    domain += search
            return domain

        # search domains
        domain_search = {}
        if post.get('search'):
            domain_search["search"] += ['|',
                ('name', 'ilike', "%%%s%%" % post.get("search")),
                ('website_description', 'ilike', "%%%s%%" % post.get("search"))]
        if post.get("grade", "all") != 'all':
            domain_search["grade"] = [("grade_id", "=", int(post.get("grade")))]
        if post.get("country", "all") != 'all':
            domain_search["country"] = [("country_id", "=", int(post.get("country")))]

        # public partner profile
        partner_ids = partner_obj.search(
            request.cr, openerp.SUPERUSER_ID, dom_without(False),
            context=request.context)
        google_map_partner_ids = ",".join([str(p) for p in partner_ids])

        # group by country
        domain = dom_without("country")
        countries = partner_obj.read_group(
            request.cr, request.uid, domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)

        partners = partner_obj.search(request.cr, request.uid, domain,
                                      context=request.context, count=True)
        countries.insert(0, {
            'country_id_count': partners,
            'country_id': ("all", _("All Countries"))
        })

        # group by grade
        domain = dom_without("grade")
        grades = partner_obj.read_group(
            request.cr, request.uid, domain, ["id", "grade_id"],
            groupby="grade_id", orderby="grade_id", context=request.context)

        grade_id_count = partner_obj.search(request.cr, request.uid, domain,
                                            count=True, context=request.context)
        grades.insert(0, {
            'grade_id_count': grade_id_count,
            'grade_id': ("all", _("All Grade"))
        })

        step = 20
        pager = request.website.pager(url="/partners/", total=len(partner_ids), page=page, step=step, scope=7, url_args=post)
        partner_ids = partner_obj.search(
            request.cr, openerp.SUPERUSER_ID, [('id', 'in', partner_ids)],
            context=request.context, limit=step, offset=pager['offset'],
            order="grade_id ASC,partner_weight DESC")
        partners = partner_obj.browse(request.cr, openerp.SUPERUSER_ID,
                                      partner_ids, request.context)

        values = {
            'countries': countries,
            'grades': grades,
            'partner_ids': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'searches': post,
            'search_path': "?%s" % urllib.urlencode(post),
        }
        return request.website.render("website_crm_partner_assign.index", values)

    @website.route(['/partners/<int:ref_id>/'], type='http', auth="public")
    def partners_ref(self, ref_id=0, **post):
        partner_obj = request.registry['res.partner']
        partner_ids = partner_obj.search(
            request.cr, openerp.SUPERUSER_ID,
            [('website_published', '=', True), ('id', '=', ref_id)],
            context=request.context)

        if not request.context['is_public_user']:
            partner_ids += partner_obj.search(
                request.cr, request.uid, [('id', '=', ref_id)],
                context=request.context)

        values = {
            'partner_id': partner_obj.browse(
                request.cr, openerp.SUPERUSER_ID, partner_ids[0],
                context=dict(request.context, show_address=True)),
        }

        return request.website.render("website_crm_partner_assign.details", values)
