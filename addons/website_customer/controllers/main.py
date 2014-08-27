# -*- coding: utf-8 -*-
import openerp
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.website.models.website import unslug
from openerp.tools.translate import _
from openerp.addons.web.http import request
import werkzeug.urls

class WebsiteCustomer(http.Controller):
    _references_per_page = 20

    @http.route([
        '/customers',
        '/customers/page/<int:page>',
        '/customers/country/<int:country_id>',
        '/customers/country/<country_name>-<int:country_id>',
        '/customers/country/<int:country_id>/page/<int:page>',
        '/customers/country/<country_name>-<int:country_id>/page/<int:page>',
    ], type='http', auth="public", website=True)
    def customers(self, country_id=0, page=0, country_name='', **post):
        cr, uid, context = request.cr, request.uid, request.context
        country_obj = request.registry['res.country']
        partner_obj = request.registry['res.partner']
        partner_name = post.get('search', '')

        domain = [('website_published', '=', True), ('assigned_partner_id', '!=', False)]
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
                country = country_obj.read(cr, uid, country_id, ['name'], context)
                if country:
                    countries.append({
                        'country_id_count': 0,
                        'country_id': (country_id, country['name'])
                    })
                countries.sort(key=lambda d: d['country_id'][1])

        countries.insert(0, {
            'country_id_count': country_count,
            'country_id': (0, _("All Countries"))
        })

        # search customers to display
        partner_count = partner_obj.search_count(cr, openerp.SUPERUSER_ID, domain, context=request.context)

        # pager
        url = '/customers'
        if country_id:
            url += '/country/%s' % country_id
        pager = request.website.pager(
            url=url, total=partner_count, page=page, step=self._references_per_page,
            scope=7, url_args=post
        )

        partner_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, domain,
                                         offset=pager['offset'], limit=self._references_per_page,
                                         context=request.context)
        google_map_partner_ids = ','.join(map(str, partner_ids))
        partners = partner_obj.browse(request.cr, openerp.SUPERUSER_ID, partner_ids, request.context)

        values = {
            'countries': countries,
            'current_country_id': country_id or 0,
            'partners': partners,
            'google_map_partner_ids': google_map_partner_ids,
            'pager': pager,
            'post': post,
            'search_path': "?%s" % werkzeug.url_encode(post),
        }
        return request.website.render("website_customer.index", values)

    # Do not use semantic controller due to SUPERUSER_ID
    @http.route(['/customers/<partner_id>'], type='http', auth="public", website=True)
    def partners_detail(self, partner_id, **post):
        _, partner_id = unslug(partner_id)
        if partner_id:
            partner = request.registry['res.partner'].browse(request.cr, SUPERUSER_ID, partner_id, context=request.context)
            if partner.exists() and partner.website_published:
                values = {}
                values['main_object'] = values['partner'] = partner
                return request.website.render("website_customer.details", values)
        return self.customers(**post)
