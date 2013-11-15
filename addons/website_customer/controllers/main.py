# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website.models import website
import urllib


class WebsiteCustomer(http.Controller):
    _references_per_page = 20

    @website.route([
        '/customers/', '/customers/page/<int:page>/',
        '/customers/country/<int:country_id>', '/customers/country/<int:country_id>/page/<int:page>/'
    ], type='http', auth="public", multilang=True)
    def customers(self, country_id=None, page=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        partner_obj = request.registry['res.partner']
        partner_name = post.get('search', '')

        base_domain = [('website_published','=',True)]
        domain = list(base_domain)
        if partner_name:
            domain += [
                '|',
                ('name', 'ilike', "%%%s%%" % post.get("search")),
                ('website_description', 'ilike', "%%%s%%" % post.get("search"))
            ]
        if country_id:
            domain += [('country_id', '=', country_id)]

        # group by country, based on all customers (base domain)
        countries = partner_obj.read_group(
            cr, uid, base_domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        country_count = partner_obj.search(
            cr, uid, base_domain, count=True, context=request.context)
        countries.insert(0, {
            'country_id_count': country_count,
            'country_id': (0, _("All Countries"))
        })

        # search customers to display
        partner_ids = partner_obj.search(cr, uid, domain, context=request.context)
        google_map_partner_ids = ",".join([str(p) for p in partner_ids])

        # pager
        pager = request.website.pager(
            url="/customers/", total=len(partner_ids), page=page, step=self._references_per_page,
            scope=7, url_args=post
        )

        # browse page of customers to display
        partner_ids = partner_obj.search(
            cr, uid, domain,
            limit=self._references_per_page, offset=pager['offset'], context=context)
        partners = partner_obj.browse(request.cr, request.uid,
                                      partner_ids, request.context)

        values = {
            'countries': countries,
            'current_country_id': country_id or 0,
            'partner_ids': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'post': post,
            'search_path': "?%s" % urllib.urlencode(post),
        }
        return request.website.render("website_customer.index", values)

    @website.route(['/customers/<model("res.partner"):partner>/'], type='http', auth="public", multilang=True)
    def customer(self, partner=None, **post):
        """ Route for displaying a single partner / customer. """
        values = {
            'partner': partner
        }
        return request.website.render("website_customer.details", values)
