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
        if request.context['is_public_user']:
            base_line_domain = [('partner.website_published', '=', True)]
        else:
            base_line_domain = [(1, '=', 1)]
        if membership_id:
            base_line_domain += [('membership_id', '=', membership_id)]
            membership = product_obj.browse(cr, openerp.SUPERUSER_ID, membership_id, context=context)
        else:
            membership = None
        if post_name:
            base_line_domain += ['|', ('partner.name', 'ilike', "%%%s%%" % post_name), ('partner.website_description', 'ilike', "%%%s%%" % post_name)]

        if request.context['is_public_user']:
            where = "r.website_published = True"
        else:
            where = "1 = 1"
        if membership_id:
            where += " and m.membership_id = "+ membership_id
            membership = product_obj.browse(cr, openerp.SUPERUSER_ID, membership_id, context=context)
        else:
            membership = None
        if post_name:
            where += " and (r.name ilike '%%%s%%'" % post_name + " or r.website_description ilike '%%%s%%'" % post_name + ")"

        query = 'select m.id from membership_membership_line m, product_product p, res_partner r where m.membership_id=p.id and m.partner=r.id and '+ where + ' order by m.membership_id, m.member_price DESC'
        cr.execute(query)
        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]
        search_membership_ids = _uniquify_list([x[0] for x in cr.fetchall()])
        # group by country, based on all customers (base domain)
        membership_line_ids = membership_line_obj.search(cr, uid, base_line_domain, context=context)
        countries = partner_obj.read_group(
            cr, uid, [('member_lines', 'in', membership_line_ids)], ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        countries_total = sum([country_dict['country_id_count'] for country_dict in countries])
        countries.insert(0, {
            'country_id_count': countries_total,
            'country_id': (0, _("All Countries"))
        })

        # displayed membership lines
        line_domain = list(base_line_domain)
        if post_country_id:
            line_domain += [('partner.country_id', '=', post_country_id)]

        membership_line_ids = membership_line_obj.search(cr, uid, line_domain, order='membership_id', context=context)
        membership_lines = membership_line_obj.browse(cr, uid, search_membership_ids, context=context)
        partner_ids = [m.partner and m.partner.id for m in membership_lines]
        google_map_partner_ids = ",".join([str(pid) for pid in partner_ids])

        # format domain for group_by and memberships
        membership_domain = [('membership', '=', True)]
        membership_ids = product_obj.search(cr, openerp.SUPERUSER_ID, membership_domain, context=context)
        memberships = product_obj.browse(cr, openerp.SUPERUSER_ID, membership_ids, context=context)

        # request pager for lines
        pager = request.website.pager(url="/members/", total=len(membership_line_ids), page=page, step=self._references_per_page, scope=7, url_args=post)
        membershipcount = {}
        total = 0
        for memeberid in membership_ids:
            count = membership_line_obj.search(cr, uid, [('membership_id', '=', memeberid)], context=context)
            membershipcount[memeberid] = len(count)
            total += len(count)
        membershipcount['total'] = total
        values = {
            'membership_count': membershipcount,
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

    @website.route(['/members/<int:partner_id>/'], type='http', auth="public", multilang=True)
    def partners_ref(self, partner_id=0, **post):
        partner_obj = request.registry['res.partner']
        if request.context['is_public_user']:
            partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [('website_published', '=', True), ('id', '=', partner_id)], context=request.context)
        else:
            partner_ids = partner_obj.search(request.cr, request.uid, [('id', '=', partner_id)], context=request.context)
        if not partner_ids:
            return self.members(post)

        values = {
            'partner_id': partner_obj.browse(
                request.cr, openerp.SUPERUSER_ID, partner_ids[0],
                context=dict(request.context, show_address=True)),
        }
        return request.website.render("website_membership.partner", values)
