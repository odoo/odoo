# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
import urllib

class website_crm_partner_assign(http.Controller):

    @http.route(['/partners/', '/partners/page/<int:page>/'], type='http', auth="public")
    def partners(self, page=0, **post):
        website = request.registry['website']
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
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, dom_without(False) )
        google_map_partner_ids = ",".join([str(p) for p in partner_ids])


        # group by country
        domain = dom_without("country")
        countries = partner_obj.read_group(request.cr, request.uid, domain, ["id", "country_id"], groupby="country_id", orderby="country_id")
        countries.insert(0, {'country_id_count': partner_obj.search(request.cr, request.uid, domain, count=True), 'country_id': ("all", _("All Countries"))})
        
        # group by grade
        domain = dom_without("grade")
        grades = partner_obj.read_group(request.cr, request.uid, domain, ["id", "grade_id"], groupby="grade_id", orderby="grade_id")
        grades.insert(0, {'grade_id_count': partner_obj.search(request.cr, request.uid, domain, count=True), 'grade_id': ("all", _("All Grade"))})
        

        step = 20
        pager = website.pager(url="/partners/", total=len(partner_ids), page=page, step=step, scope=7, url_args=post)
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [('id', 'in', partner_ids)], 
            limit=step, offset=pager['offset'], order="grade_id ASC,partner_weight DESC")


        values = website.get_rendering_context({
            'countries': countries,
            'grades': grades,
            'partner_ids': partner_obj.browse(request.cr, openerp.SUPERUSER_ID, partner_ids),
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'searches': post,
            'search_path': "?%s" % urllib.urlencode(post),
        })
        return website.render("website_crm_partner_assign.index", values)

    @http.route(['/partners/<int:ref_id>/'], type='http', auth="public")
    def partners_ref(self, ref_id=0, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [('website_published', '=', True), ('id', '=', ref_id)])
        if request.uid != website.get_public_user().id:
            partner_ids += partner_obj.search(request.cr, request.uid, [('id', '=', ref_id)])

        values = website.get_rendering_context({
            'partner_id': partner_obj.browse(request.cr, openerp.SUPERUSER_ID, partner_ids[0], context={'show_address': True}),
        })
        return website.render("website_crm_partner_assign.details", values)

