# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website import website
import urllib

class website_crm_partner_assign(http.Controller):

    @website.route(['/members/', '/members/page/<int:page>/'], type='http', auth="public")
    def members(self, page=0, **post):
        website = request.registry['website']
        membership_obj = request.registry['membership.membership_line']

        def dom_without(without):
            domain = openerp.SUPERUSER_ID != request.uid and [('partner.website_published', '=', True)] or [(1, "=", 1)]
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
        if post.get("membership_id", "all") != 'all':
            domain_search["membership"] = [("membership", "=", int(post.get("membership")))]

        # public membership
        membership_ids = membership_obj.search(request.cr, openerp.SUPERUSER_ID, dom_without(False), context=request.context)
        memberships = membership_obj.browse(request.cr, openerp.SUPERUSER_ID, membership_ids, request.context)
        google_map_partner_ids = ",".join([str(m.partner.id) for m in memberships])

        # group by membership_id
        domain = dom_without("membership")
        memberships = membership_obj.read_group(request.cr, request.uid, domain, ["id", "membership_id"], groupby="membership_id", orderby="membership_id", context=request.context)
        memberships.insert(0, {'membership_id_count': membership_obj.search(request.cr, request.uid, domain, count=True, context=request.context), 'membership_id': ("all", _("All Groups"))})

        step = 20
        pager = website.pager(url="/members/", total=len(membership_ids), page=page, step=step, scope=7, url_args=post)
        membership_ids = membership_obj.search(
            request.cr, openerp.SUPERUSER_ID, [('id', 'in', membership_ids)],
            limit=step, offset=pager['offset'], order="membership_id ASC,date DESC",
            context=request.context)

        values = {
            'memberships': memberships,
            'membership_line_ids': membership_obj.browse(request.cr, openerp.SUPERUSER_ID, membership_ids, request.context),
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'searches': post,
            'search_path': "?%s" % urllib.urlencode(post),
        }
        return request.webcontext.render("website_membership.index", values)

    @website.route(['/members/<int:ref_id>/'], type='http', auth="public")
    def partners_ref(self, ref_id=0, **post):
        partner_obj = request.registry['res.partner']
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [('website_published', '=', True), ('id', '=', ref_id)], context=request.context)
        if not request.webcontext.is_public_user:
            partner_ids += partner_obj.search(request.cr, request.uid, [('id', '=', ref_id)], context=request.context)

        context = request.context.copy()
        context.update({'show_address': True})
        values = {
            'partner_id': partner_obj.browse(
                request.cr, openerp.SUPERUSER_ID, partner_ids[0],
                context=context),
        }
        return request.webcontext.render("website_membership.details", values)
