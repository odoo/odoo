# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website


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
        post_name = post.get('search', '')

        # format displayed membership lines domain
        if request.context['is_public_user']:
            line_domain = [('partner.website_published', '=', True)]
        else:
            line_domain = [(1, '=', 1)]
        if membership_id:
            line_domain += [('membership_id', '=', membership_id)]
        if post_name:
            line_domain += ['|', ('partner.name', 'ilike', "%%%s%%" % post_name), ('partner.website_description', 'ilike', "%%%s%%" % post_name)]

        membership_line_ids = membership_line_obj.search(cr, uid, line_domain, context=context)
        membership_lines = membership_line_obj.browse(cr, uid, membership_line_ids, context=context)
        google_map_partner_ids = ",".join([str(m.partner.id) for m in membership_lines])

        # format domain for group_by and memberships
        membership_domain = [('membership', '=', True)]
        membership_ids = product_obj.search(cr, openerp.SUPERUSER_ID, membership_domain, context=context)
        memberships = product_obj.browse(cr, openerp.SUPERUSER_ID, membership_ids, context=context)

        # request pager for lines
        pager = request.website.pager(url="/members/", total=len(membership_line_ids), page=page, step=self._references_per_page, scope=7, url_args=post)

        values = {
            'membership_line_ids': membership_lines,
            'membership_ids': memberships,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'name_search': post_name,
        }
        return request.website.render("website_membership.index", values)

    @website.route(['/members/<int:partner_id>/'], type='http', auth="public", multilang=True)
    def partners_ref(self, partner_id=0, **post):
        partner_obj = request.registry['res.partner']
        if request.context['is_public_user']:
            partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [('website_pushished', '=', True), ('id', '=', partner_id)], context=request.context)
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
