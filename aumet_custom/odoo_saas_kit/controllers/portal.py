# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################

import base64

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
import logging
_logger = logging.getLogger(__name__)


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaasContract = request.env['saas.contract']
        saas_contract_count = SaasContract.search_count([
            ('partner_id', '=', partner.commercial_partner_id.id),
        ])
        values.update({
            'saas_contract_count': saas_contract_count,
        })
        return values

    def _contract_check_access(self, contract_id, access_token=None):
        contract = request.env['saas.contract'].browse([contract_id])
        contract_sudo = contract.sudo()
        partner = request.env.user.partner_id
        try:
            if contract.exists():
                if partner.id != contract.partner_id.id:
                    raise AccessError("Not Allowed")
                else:
                    contract.check_access_rights('read')
                    contract.check_access_rule('read')
            else:
                _logger.info("------------------ No Record Found--------")
                raise AccessError("Not allowed")
        except AccessError:
            _logger.info("-------------5-----------")
            if contract.exists():
                if not access_token or not consteq(contract_sudo.access_token, access_token):
                    raise
            else:
                raise
        return contract_sudo

    @http.route(['/my/saas/contracts', '/my/saas/contracts/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_contracts(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaasContract = request.env['saas.contract']
        domain = [
            ('partner_id', '=', partner.commercial_partner_id.id)
        ]
        searchbar_sortings = {
            'date': {'label': _('Purchase Date'), 'contract': 'start_date desc'},
        }
        if not sortby:
            sortby = 'date'
        sort_contract = searchbar_sortings[sortby]['contract']
        if date_begin and date_end:
            domain += [('start_date', '>', date_begin), ('start_date', '<=', date_end)]
        saas_contract_count = SaasContract.search_count(domain)
        pager = portal_pager(
            url='/my/saas/contracts',
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sort_by': sortby},
            total=saas_contract_count,
            page=page,
            step=self._items_per_page
        )
        contracts = SaasContract.search(domain, order=sort_contract, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_session_history'] = contracts.ids[:100]
        values.update({
            'date': date_begin,
            'contracts': contracts.sudo(),
            'page_name': 'contract',
            'pager': pager,
            'default_url': '/my/saas/contracts',
            'searchbar_sorting': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("odoo_saas_kit.portal_my_saas_contracts", values)

    def _contract_get_page_view_values(self, contract, access_token, **kwargs):
        values = {
            'contract': contract,
        }
        if access_token:
            values['no_breadcrumbs'] = True
            values['access_token'] = access_token
        if kwargs.get('error'):
            values['error'] = kwargs['error']
        if kwargs.get('warning'):
            values['warning'] = kwargs['warning']
        if kwargs.get('success'):
            values['success'] = kwargs['success']

        history = request.session.get('my_session_history', [])
        values.update(get_records_pager(history, contract))
        return values

    @http.route(['/my/saas/contract/<int:contract>'], type='http', auth="user", website=True)
    def portal_contract_page(self, contract=None, access_token=None, **kw):
        try:
            contract_sudo = self._contract_check_access(contract, access_token)
        except AccessError:
            return request.redirect('/my')
        except Exception:
            _logger.info("-------- Unknown Error-------")
            return request.redirect('/my')
        values = self._contract_get_page_view_values(contract_sudo, access_token, **kw)
        return request.render("odoo_saas_kit.portal_contract_page", values)
