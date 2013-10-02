# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website.models import website
import urllib


class website_contract(http.Controller):

    @website.route(['/references/', '/references/page/<int:page>/'], type='http', auth="public")
    def references(self, page=0, **post):
        partner_obj = request.registry['res.partner']
        account_obj = request.registry['account.analytic.account']

        # check contracts
        contract_ids = account_obj.search(request.cr, openerp.SUPERUSER_ID, [(1, "=", 1)])
        contracts = account_obj.browse(request.cr, openerp.SUPERUSER_ID,
                                       contract_ids, request.context)
        contract_project_ids = [contract.partner_id.id for contract in contracts
                                if contract.partner_id]
        domain = ['|', ('id', "in", contract_project_ids), ('id', "child_of", contract_project_ids)]

        if post.get('search'):
            domain += [
                '|',
                ('name', 'ilike', "%%%s%%" % post.get("search")),
                ('website_description', 'ilike', "%%%s%%" % post.get("search"))
            ]
        if request.context['is_public_user']:
            domain = ['&'] + domain + [('website_published', '=', True)]

        # public partner profile
        partner_ids = partner_obj.search(
            request.cr, openerp.SUPERUSER_ID,
            domain + [('website_published', '=', True)], context=request.context)
        google_map_partner_ids = ",".join([str(p) for p in partner_ids])

        # group by country
        countries = partner_obj.read_group(
            request.cr, request.uid, domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        country_count = partner_obj.search(
            request.cr, request.uid, domain, count=True, context=request.context)
        countries.insert(0, {
            'country_id_count': country_count,
            'country_id': ("all", _("All Countries"))
        })

        if post.get("country", "all") != 'all':
            partner_ids = partner_obj.search(
                request.cr, request.uid,
                [
                    ('id', 'in', partner_ids),
                    ('country_id', '=', int(post.get('country')))
                ], context=request.context)

        step = 20
        pager = request.website.pager(url="/references/", total=len(partner_ids), page=page, step=step, scope=7, url_args=post)
        partner_ids = partner_obj.search(
            request.cr, openerp.SUPERUSER_ID, [('id', 'in', partner_ids)],
            limit=step, offset=pager['offset'], context=request.context)
        partners = partner_obj.browse(request.cr, openerp.SUPERUSER_ID,
                                      partner_ids, request.context)
        values = {
            'countries': countries,
            'partner_ids': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'searches': post,
            'search_path': "?%s" % urllib.urlencode(post),
        }
        return request.website.render("website_contract.index", values)

    @website.route(['/references/<int:partner_id>/'], type='http', auth="public")
    def references_ref(self, partner_id=None, **post):
        """ Route for displaying a single partner.

        :param integer partner_id: partner to display. If not set or not valid
                                   call basic references method.
        """
        partner_obj = request.registry['res.partner']
        if request.context['is_public_user']:
            partner_ids = partner_obj.search(
                request.cr, openerp.SUPERUSER_ID, [
                    ('website_published', '=', True),
                    ('id', '=', partner_id)
                ], context=request.context)
            partner_id = partner_ids and partner_ids[0] or None

        if not partner_id:
            return self.references(post)

        values = {
            'partner_id': partner_obj.browse(
                request.cr, openerp.SUPERUSER_ID, partner_id,
                dict(request.context, show_address=True)),
        }

        return request.website.render("website_contract.details", values)
