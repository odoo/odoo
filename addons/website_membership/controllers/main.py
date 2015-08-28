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
        '/members/association/<membership_id>',
        '/members/association/<membership_id>/page/<int:page>',

        '/members/country/<int:country_id>',
        '/members/country/<country_name>-<int:country_id>',
        '/members/country/<int:country_id>/page/<int:page>',
        '/members/country/<country_name>-<int:country_id>/page/<int:page>',

        '/members/association/<membership_id>/country/<country_name>-<int:country_id>',
        '/members/association/<membership_id>/country/<int:country_id>',
        '/members/association/<membership_id>/country/<country_name>-<int:country_id>/page/<int:page>',
        '/members/association/<membership_id>/country/<int:country_id>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def members(self, membership_id=None, country_name=None, country_id=0, page=1, **post):
        cr, uid, context = request.cr, request.uid, request.context
        product_obj = request.registry['product.product']
        country_obj = request.registry['res.country']
        membership_line_obj = request.registry['membership.membership_line']
        partner_obj = request.registry['res.partner']
        post_name = post.get('name', '')
        current_country = None

        # base domain for groupby / searches
        base_line_domain = [("partner.website_published", "=", True), ('state', 'in', ['free', 'paid'])]
        if membership_id and membership_id != 'free':
            membership_id = int(membership_id)
            base_line_domain.append(('membership_id', '=', membership_id))
            membership = product_obj.browse(cr, uid, membership_id, context=context)
        else:
            membership = None
        if post_name:
            base_line_domain += ['|', ('partner.name', 'ilike', post_name),
                                      ('partner.website_description', 'ilike', post_name)]

        # group by country, based on all customers (base domain)
        if membership_id != 'free':
            membership_line_ids = membership_line_obj.search(cr, SUPERUSER_ID, base_line_domain, context=context)
            country_domain = [('member_lines', 'in', membership_line_ids)]
        else:
            membership_line_ids = []
            country_domain = [('membership_state', '=', 'free')]
            if post_name:
                country_domain += ['|', ('name', 'ilike', post_name),
                                      ('website_description', 'ilike', post_name)]
        countries = partner_obj.read_group(
            cr, SUPERUSER_ID, country_domain + [("website_published", "=", True)], ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        countries_total = sum(country_dict['country_id_count'] for country_dict in countries)

        line_domain = list(base_line_domain)
        if country_id:
            line_domain.append(('partner.country_id', '=', country_id))
            current_country = country_obj.read(cr, uid, country_id, ['id', 'name'], context)
            if not any(x['country_id'][0] == country_id for x in countries if x['country_id']):
                countries.append({
                    'country_id_count': 0,
                    'country_id': (country_id, current_country["name"])
                })
                countries = filter(lambda d:d['country_id'], countries)
                countries.sort(key=lambda d: d['country_id'][1])

        countries.insert(0, {
            'country_id_count': countries_total,
            'country_id': (0, _("All Countries"))
        })

        # format domain for group_by and memberships
        membership_ids = product_obj.search(cr, uid, [('membership', '=', True)], order="website_sequence", context=context)
        memberships = product_obj.browse(cr, uid, membership_ids, context=context)
        # make sure we don't access to lines with unpublished membershipts
        line_domain.append(('membership_id', 'in', membership_ids))

        limit = self._references_per_page
        offset = limit * (page - 1)

        count_members = 0
        membership_line_ids = []
        # displayed non-free membership lines
        if membership_id != 'free':
            count_members = membership_line_obj.search_count(cr, SUPERUSER_ID, line_domain, context=context)
            if offset <= count_members:
                membership_line_ids = tuple(membership_line_obj.search(cr, SUPERUSER_ID, line_domain, offset, limit, context=context))
        membership_lines = membership_line_obj.browse(cr, uid, membership_line_ids, context=context)
        # TODO: Following line can be deleted in master. Kept for retrocompatibility.
        membership_lines = sorted(membership_lines, key=lambda x: x.membership_id.website_sequence)
        page_partner_ids = set(m.partner.id for m in membership_lines)

        google_map_partner_ids = []
        if request.env.ref('website_membership.opt_index_google_map').customize_show:
            membership_lines_ids = membership_line_obj.search(cr, uid, line_domain, context=context)
            google_map_partner_ids = membership_line_obj.get_published_companies(cr, uid, membership_line_ids, limit=2000, context=context)

        search_domain = [('membership_state', '=', 'free'), ('website_published', '=', True)]
        if post_name:
            search_domain += ['|', ('name', 'ilike', post_name), ('website_description', 'ilike', post_name)]
        if country_id:
            search_domain += [('country_id', '=', country_id)]
        free_partner_ids = partner_obj.search(cr, SUPERUSER_ID, search_domain, context=context)
        memberships_data = []
        for membership_record in memberships:
            memberships_data.append({'id': membership_record.id, 'name': membership_record.name})
        memberships_partner_ids = {}
        for line in membership_lines:
            memberships_partner_ids.setdefault(line.membership_id.id, []).append(line.partner.id)
        if free_partner_ids:
            memberships_data.append({'id': 'free', 'name': _('Free Members')})
            if not membership_id or membership_id == 'free':
                if count_members < offset + limit:
                    free_start = max(offset - count_members, 0)
                    free_end = max(offset + limit - count_members, 0)
                    memberships_partner_ids['free'] = free_partner_ids[free_start:free_end]
                    page_partner_ids |= set(memberships_partner_ids['free'])
                google_map_partner_ids += free_partner_ids[:2000-len(google_map_partner_ids)]
                count_members += len(free_partner_ids)

        google_map_partner_ids = ",".join(map(str, google_map_partner_ids))

        partners = { p.id: p for p in partner_obj.browse(request.cr, SUPERUSER_ID, list(page_partner_ids), request.context)}

        base_url = '/members%s%s' % ('/association/%s' % membership_id if membership_id else '',
                                     '/country/%s' % country_id if country_id else '')

        # request pager for lines
        pager = request.website.pager(url=base_url, total=count_members, page=page, step=limit, scope=7, url_args=post)

        values = {
            'partners': partners,
            'membership_lines': membership_lines,  # TODO: This line can be deleted in master. Kept for retrocompatibility.
            'memberships': memberships,  # TODO: This line too.
            'membership': membership,  # TODO: This line too.
            'memberships_data': memberships_data,
            'memberships_partner_ids': memberships_partner_ids,
            'membership_id': membership_id,
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
