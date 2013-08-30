# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
import urllib

class website_contract(http.Controller):

    @http.route(['/references/', '/references/page/<int:page>/'], type='http', auth="public")
    def references(self, page=0, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        account_obj = request.registry['account.analytic.account']

        # check contracts
        contract_ids = account_obj.search(request.cr, openerp.SUPERUSER_ID, [(1, "=", 1)])
        contract_project_ids = [contract.partner_id.id 
            for contract in account_obj.browse(request.cr, openerp.SUPERUSER_ID, contract_ids) if contract.partner_id]
        domain = ['|', ('id', "in", contract_project_ids), ('id', "child_of", contract_project_ids)]

        if post.get('search'):
            domain += ['|',
                ('name', 'ilike', "%%%s%%" % post.get("search")), 
                ('website_description', 'ilike', "%%%s%%" % post.get("search"))]


        # public partner profile
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, domain + [('website_published', '=', True)])
        google_map_partner_ids = ",".join([str(p) for p in partner_ids])

        if request.uid != website.get_public_user().id:
            # search without website_published
            partner_ids += partner_obj.search(request.cr, request.uid, domain)
            partner_ids = list(set(partner_ids))


        # group by country
        countries = partner_obj.read_group(request.cr, request.uid, domain, ["id", "country_id"], groupby="country_id", orderby="country_id")
        countries.insert(0, {'country_id_count': partner_obj.search(request.cr, request.uid, domain, count=True), 'country_id': ("all", _("All Countries"))})


        if post.get("country", "all") != 'all':
            partner_ids = partner_obj.search(request.cr, request.uid, [('id', 'in', partner_ids), ('country_id', '=', int(post.get('country')))])


        step = 20
        pager = website.pager(url="/references/", total=len(partner_ids), page=page, step=step, scope=7, url_args=post)
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [('id', 'in', partner_ids)], limit=step, offset=pager['offset'])


        values = website.get_rendering_context({
            'countries': countries,
            'partner_ids': partner_obj.browse(request.cr, openerp.SUPERUSER_ID, partner_ids),
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'searches': post,
            'search_path': "?%s" % urllib.urlencode(post),
        })
        return website.render("website_contract.index", values)

    @http.route(['/references/<int:ref_id>/'], type='http', auth="public")
    def references_ref(self, ref_id=0, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [('website_published', '=', True), ('id', '=', ref_id)])
        if request.uid != website.get_public_user().id:
            partner_ids += partner_obj.search(request.cr, request.uid, [('id', '=', ref_id)])

        values = website.get_rendering_context({
            'partner_id': partner_obj.browse(request.cr, openerp.SUPERUSER_ID, partner_ids[0], context={'show_address': True}),
        })
        return website.render("website_contract.details", values)

