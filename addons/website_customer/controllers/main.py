# -*- coding: utf-8 -*-

import openerp
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.addons.web.http import request
from openerp.addons.website_partner.controllers import main as website_partner
import werkzeug.urls

class WebsiteCustomer(http.Controller):
    _references_per_page = 20

    @http.route([
        '/customers/',
        '/customers/page/<int:page>/',
        '/customers/country/<int:country_id>',
        '/customers/country/<country_name>-<int:country_id>',
        '/customers/country/<int:country_id>/page/<int:page>/',
        '/customers/country/<country_name>-<int:country_id>/page/<int:page>/',
    ], type='http', auth="public", website=True, multilang=True)
    def customers(self, country_id=0, page=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        country_obj = request.registry['res.country']
        partner_obj = request.registry['res.partner']
        partner_name = post.get('search', '')

        base_domain = [('website_published','=',True)]
        domain = list(base_domain)
        if partner_name:
            domain += [
                '|',
                ('name', 'ilike', post.get("search")),
                ('website_description', 'ilike', post.get("search"))
            ]

        # group by country, based on customers found with the search(domain)
        countries = partner_obj.read_group(
            cr, openerp.SUPERUSER_ID, domain, ["id", "country_id"],
            groupby="country_id", orderby="country_id", context=request.context)
        country_count = partner_obj.search(
            cr, openerp.SUPERUSER_ID, domain, count=True, context=request.context)

        if country_id:
            domain += [('country_id', '=', country_id)]
            if not any(x['country_id'][0] == country_id for x in countries):
                country = country_obj.browse(cr, uid, country_id, context)
                countries.append({
                    'country_id_count': 0,
                    'country_id': (country_id, country.name)
                })
                countries.sort(key=lambda d: d['country_id'][1])

        countries.insert(0, {
            'country_id_count': country_count,
            'country_id': (0, _("All Countries"))
        })

        # search customers to display
        partner_ids = partner_obj.search(cr, openerp.SUPERUSER_ID, domain, context=request.context)
        google_map_partner_ids = ",".join([str(p) for p in partner_ids])

        # pager
        url = '/customers/'
        if country_id:
            url += 'country/%s/' % country_id
        pager = request.website.pager(
            url=url, total=len(partner_ids), page=page, step=self._references_per_page,
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
            'search_path': "?%s" % werkzeug.url_encode(post),
        }
        return request.website.render("website_customer.index", values)

    @http.route(['/customers/<int:partner_id>/', '/customers/<partner_name>-<int:partner_id>/'], type='http', auth="public", website=True, multilang=True)
    def customer(self, partner_id, **post):
        partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_id, context=request.context)
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
