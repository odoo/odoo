# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.tools.translate import _

import urllib


class WebsiteMembership(http.Controller):
    _references_per_page = 20

    @website.route([
        '/members/',
        '/members/page/<int:page>/',
        '/members/association/<int:membership_id>/',
        '/members/association/<int:membership_id>/page/<int:page>/',
    ], type='http', auth="public", multilang=True)
    def members(self, membership_id=None, page=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        product_obj = request.registry['product.product']
        membership_line_obj = request.registry['membership.membership_line']
        partner_obj = request.registry['res.partner']
        post_name = post.get('name', '')
        post_country_id = int(post.get('country_id', '0'))

        # base domain for groupby / searches
        base_line_domain = []
        if membership_id:
            base_line_domain.append(('membership_id', '=', membership_id))
            membership = product_obj.browse(cr, uid, membership_id, context=context)
        else:
            membership = None
        if post_name:
            base_line_domain += ['|', ('partner.name', 'ilike', "%%%s%%" % post_name), ('partner.website_description', 'ilike', "%%%s%%" % post_name)]

        # group by country, based on all customers (base domain)
        membership_line_ids = membership_line_obj.search(cr, uid, base_line_domain, context=context)
        countries = partner_obj.read_group(
            cr, uid, [('member_lines', 'in', membership_line_ids)], ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        countries_total = sum(country_dict['country_id_count'] for country_dict in countries)
        countries.insert(0, {
            'country_id_count': countries_total,
            'country_id': (0, _("All Countries"))
        })

        # displayed membership lines
        line_domain = list(base_line_domain)
        if post_country_id:
            line_domain.append(('partner.country_id', '=', post_country_id))

        membership_line_ids = membership_line_obj.search(cr, uid, line_domain, context=context)
        membership_lines = membership_line_obj.browse(cr, uid, membership_line_ids, context=context)
        partner_ids = [m.partner and m.partner.id for m in membership_lines]
        google_map_partner_ids = ",".join(map(str, partner_ids))

        # format domain for group_by and memberships
        membership_ids = product_obj.search(cr, uid, [('membership', '=', True)], context=context)
        memberships = product_obj.browse(cr, uid, membership_ids, context=context)

        # request pager for lines
        pager = request.website.pager(url="/members/", total=len(membership_line_ids), page=page, step=self._references_per_page, scope=7, url_args=post)

        values = {
            'membership_lines': membership_lines,
            'memberships': memberships,
            'membership': membership,
            'countries': countries,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'post': post,
            'search': "?%s" % urllib.urlencode(post),
        }
        return request.website.render("website_membership.index", values)

    @website.route(['/members/<model("res.partner"):partner>/'], type='http', auth="public", multilang=True)
    def partners_ref(self, partner, **post):
        if not partner.exists():
            return self.members(**post)

        values = {
            'partner_id': request.registry['res.partner'].browse(
                request.cr, request.uid, partner.id,
                context=dict(request.context, show_address=True)),
        }
        return request.website.render("website_membership.partner", values)
