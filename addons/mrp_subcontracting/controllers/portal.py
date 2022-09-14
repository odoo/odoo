# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug
from collections import OrderedDict

from odoo import conf, http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class CustomerPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'production_count' in counters:
            commercial_partner = request.env.user.partner_id.commercial_partner_id
            values['production_count'] = request.env['stock.picking'].search_count([('partner_id.commercial_partner_id', '=', commercial_partner.id), ('move_ids.is_subcontract', '=', True)])
        return values

    @http.route(['/my/productions', '/my/productions/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_productions(self, page=1, date_begin=None, date_end=None, sortby='date', filterby='all'):
        commercial_partner = request.env.user.partner_id.commercial_partner_id
        StockPicking = request.env['stock.picking']
        domain = [('partner_id.commercial_partner_id', '=', commercial_partner.id), ('move_ids.is_subcontract', '=', True)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'done': {'label': _('Done'), 'domain': [('state', '=', 'done')]},
            'ready': {'label': _('Ready'), 'domain': [('state', '=', 'assigned')]},
        }
        domain += searchbar_filters[filterby]['domain']

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
        }
        order = searchbar_sortings[sortby]['order']
        # count for pager
        count = StockPicking.search_count(domain)
        # make pager
        pager = portal_pager(
            url='/my/productions',
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=count,
            page=page,
            step=self._items_per_page
        )
        # search the pickings to display, according to the pager data
        pickings = StockPicking.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        values = {
            'date': date_begin,
            'pickings': pickings,
            'page_name': 'production',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/productions',
        }

        return http.request.render("mrp_subcontracting.portal_my_productions", values)

    @http.route("/my/productions/<int:picking_id>", type="http", auth="user", methods=['GET'], website=True)
    def portal_my_production(self, picking_id):
        try:
            self._document_check_access('stock.picking', picking_id)
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound
        return request.render("mrp_subcontracting.subcontracting_portal", {'picking_id': picking_id})

    @http.route("/my/productions/<int:picking_id>/subcontracting_portal", type="http", auth="user", methods=['GET'])
    def render_production_backend_view(self, picking_id):
        try:
            picking = self._document_check_access('stock.picking', picking_id)
        except (AccessError, MissingError):
            raise werkzeug.exceptions.NotFound
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        mods = conf.server_wide_modules or []
        lang = user_context.get("lang")
        translation_hash = request.env['ir.translation'].get_web_translations_hash(mods, lang)
        cache_hashes = {
            "translations": translation_hash,
        }
        production_company = picking.company_id
        session_info.update(
            cache_hashes=cache_hashes,
            action_name='mrp_subcontracting.subcontracting_portal_view_production_action',
            picking_id=picking.id,
            user_companies={
                'current_company': production_company.id,
                'allowed_companies': {
                    production_company.id: {
                        'id': production_company.id,
                        'name': production_company.name,
                    },
                },
            })

        return request.render(
            'mrp_subcontracting.subcontracting_portal_embed',
            {'session_info': session_info},
        )
