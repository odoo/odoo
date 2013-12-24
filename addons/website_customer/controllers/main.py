# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.addons.website_partner.controllers import main as website_partner
import urllib


class WebsiteCustomer(http.Controller):
    _references_per_page = 20

    @website.route([
        '/customers/',
        '/customers/page/<int:page>/',
        '/customers/country/<model("res.country"):country>',
        '/customers/country/<model("res.country"):country>/page/<int:page>/'
    ], type='http', auth="public", multilang=True)
    def customers(self, country=None, page=0, **post):
        website.preload_records(country)
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
        country_id = None
        if country:
            domain += [('country_id', '=', country.id)]
            country_id = country.id

        # group by country, based on all customers (base domain)
        countries = partner_obj.read_group(
            cr, openerp.SUPERUSER_ID, base_domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        country_count = partner_obj.search(
            cr, openerp.SUPERUSER_ID, base_domain, count=True, context=request.context)
        countries.insert(0, {
            'country_id_count': country_count,
            'country_id': (0, _("All Countries"))
        })

        # search customers to display
        partner_ids = partner_obj.search(cr, openerp.SUPERUSER_ID, domain, context=request.context)
        google_map_partner_ids = ",".join([str(p) for p in partner_ids])

        # pager
        pager = request.website.pager(
            url="/customers/", total=len(partner_ids), page=page, step=self._references_per_page,
            scope=7, url_args=post
        )

        # browse page of customers to display
        partner_ids = partner_obj.search(
            cr, openerp.SUPERUSER_ID, domain,
            limit=self._references_per_page, offset=pager['offset'], context=context)
        partners_data = partner_obj.read(
            request.cr, openerp.SUPERUSER_ID, partner_ids, request.website.get_partner_white_list_fields(), context=request.context)
        values = {
            'countries': countries,
            'current_country_id': country_id or 0,
            'partners_data': partners_data,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'post': post,
            'search_path': "?%s" % urllib.urlencode(post),
        }
        return request.website.render("website_customer.index", values)

    @website.route(['/customers/<model("res.partner"):partner>/'], type='http', auth="public", multilang=True)
    def customer(self, partner, **post):
        website.preload_records(partner)
        values = website_partner.get_partner_template_value(partner)
        if not values:
            return self.customers(**post)

        partner_obj = request.registry['res.partner']
        if values['partner_data'].get('assigned_partner_id', None):
            values['assigned_partner_data'] = partner_obj.read(
                request.cr, openerp.SUPERUSER_ID, [values['partner_data']['assigned_partner_id'][0]],
                request.website.get_partner_white_list_fields(), context=request.context)[0]
        if values['partner_data'].get('implemented_partner_ids', None):
            implemented_partners_data = partner_obj.read(
                request.cr, openerp.SUPERUSER_ID, values['partner_data']['implemented_partner_ids'],
                request.website.get_partner_white_list_fields(), context=request.context)
            values['implemented_partners_data'] = []
            for data in implemented_partners_data:
                if data.get('website_published'):
                    values['implemented_partners_data'].append(data)

        values['main_object'] = values['partner']
        return request.website.render("website_customer.details", values)
