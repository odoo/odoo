# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models.website import unslug
from openerp.tools.translate import _

import werkzeug.urls


class WebsiteMembership(http.Controller):
    _references_per_page = 20

    @http.route([
        '/members',
        '/members/page/<int:page>',
        '/members/association/<int:membership_id>',
        '/members/association/<int:membership_id>/page/<int:page>',

        '/members/country/<int:country_id>',
        '/members/country/<country_name>-<int:country_id>',
        '/members/country/<int:country_id>/page/<int:page>',
        '/members/country/<country_name>-<int:country_id>/page/<int:page>',

        '/members/association/<int:membership_id>/country/<country_name>-<int:country_id>',
        '/members/association/<int:membership_id>/country/<int:country_id>',
        '/members/association/<int:membership_id>/country/<country_name>-<int:country_id>/page/<int:page>',
        '/members/association/<int:membership_id>/country/<int:country_id>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def members(self, membership_id=None, country_name=None, country_id=0, page=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        product_obj = request.registry['product.product']
        country_obj = request.registry['res.country']
        membership_line_obj = request.registry['membership.membership_line']
        partner_obj = request.registry['res.partner']
        post_name = post.get('name', '')
        current_country = None

        # base domain for groupby / searches
        base_line_domain = [("partner.website_published", "=", True), ('state', 'in', ['free', 'paid'])]
        if membership_id:
            base_line_domain.append(('membership_id', '=', membership_id))
            membership = product_obj.browse(cr, uid, membership_id, context=context)
        else:
            membership = None
        if post_name:
            base_line_domain += ['|', ('partner.name', 'ilike', post_name),
                                      ('partner.website_description', 'ilike', post_name)]

        # group by country, based on all customers (base domain)
        membership_line_ids = membership_line_obj.search(cr, uid, base_line_domain, context=context)
        countries = partner_obj.read_group(
            cr, uid, [('member_lines', 'in', membership_line_ids), ("website_published", "=", True)], ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        countries_total = sum(country_dict['country_id_count'] for country_dict in countries)

        line_domain = list(base_line_domain)
        if country_id:
            line_domain.append(('partner.country_id', '=', country_id))
            current_country = country_obj.read(cr, uid, country_id, ['id', 'name'], context)
            if not any(x['country_id'][0] == country_id for x in countries):
                countries.append({
                    'country_id_count': 0,
                    'country_id': (country_id, current_country["name"])
                })
                countries.sort(key=lambda d: d['country_id'][1])

        countries.insert(0, {
            'country_id_count': countries_total,
            'country_id': (0, _("All Countries"))
        })

        # displayed membership lines
        membership_line_ids = membership_line_obj.search(cr, uid, line_domain, context=context)
        membership_lines = membership_line_obj.browse(cr, uid, membership_line_ids, context=context)
        membership_lines.sort(key=lambda x: x.membership_id.website_sequence)
        partner_ids = [m.partner.id for m in membership_lines]
        google_map_partner_ids = ",".join(map(str, partner_ids))

        partners = dict((p.id, p) for p in partner_obj.browse(request.cr, SUPERUSER_ID, partner_ids, request.context))

        # format domain for group_by and memberships
        membership_ids = product_obj.search(cr, uid, [('membership', '=', True)], order="website_sequence", context=context)
        memberships = product_obj.browse(cr, uid, membership_ids, context=context)

        # request pager for lines
        pager = request.website.pager(url="/members", total=len(membership_line_ids), page=page, step=self._references_per_page, scope=7, url_args=post)

        values = {
            'partners': partners,
            'membership_lines': membership_lines,
            'memberships': memberships,
            'membership': membership,
            'countries': countries,
            'current_country': current_country and [current_country['id'], current_country['name']] or None,
            'current_country_id': current_country and current_country['id'] or 0,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'post': post,
            'search': "?%s" % werkzeug.url_encode(post),
        }
        return request.website.render("website_membership.index", values)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/members/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        _, partner_id = unslug(partner_id)
        if partner_id:
            partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_id, context=request.context)
            if partner.exists() and partner.website_published:
                values = {}
                values['main_object'] = values['partner'] = partner
                return request.website.render("website_membership.partner", values)
        return self.members(**post)
