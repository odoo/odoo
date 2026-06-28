# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo.addons.mail.controllers.mail import MailController
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CrmController(http.Controller):

    @http.route('/lead/case_mark_won', type='http', auth='user', methods=['GET'])
    def crm_lead_case_mark_won(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('crm.lead', int(res_id), token)
        if comparison and record:
            try:
                record.action_set_won_rainbowman()
            except Exception:
                _logger.exception("Could not mark crm.lead as won")
                return MailController._redirect_to_generic_fallback('crm.lead', res_id)
        return redirect

    @http.route('/lead/case_mark_lost', type='http', auth='user', methods=['GET'])
    def crm_lead_case_mark_lost(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('crm.lead', int(res_id), token)
        if comparison and record:
            try:
                record.action_set_lost()
            except Exception:
                _logger.exception("Could not mark crm.lead as lost")
                return MailController._redirect_to_generic_fallback('crm.lead', res_id)
        return redirect

    @http.route('/lead/convert', type='http', auth='user', methods=['GET'])
    def crm_lead_convert(self, res_id, token):
        comparison, record, redirect = MailController._check_token_and_record_or_redirect('crm.lead', int(res_id), token)
        if comparison and record:
            try:
                record.convert_opportunity(record.partner_id)
            except Exception:
                _logger.exception("Could not convert crm.lead to opportunity")
                return MailController._redirect_to_generic_fallback('crm.lead', res_id)
        return redirect

    # ===========================================================================================================================================
    # ====================================================== Gmail add-on rest api ==============================================================
    # ===========================================================================================================================================

    @http.route('/partner/get', type="json", auth="public")
    def res_partner_get_by_email(self, emails, **kwargs):

        partners = request.env['res.partner'].sudo().search([('email', 'in', emails)])
        partners_data = []

        for partner in partners:
            partners_data.append({
                'id': partner.id,
                'name': partner.name,
                'company_name': partner.parent_name,
                'address': {
                    'street': partner.street,
                    'city': partner.city,
                    'zip': partner.zip,
                    'country': partner.country_id.name
                },
                'phone': partner.phone,
                'mobile': partner.mobile,
                'email': partner.email,
                'image': partner.image_128
            })

        return {
            'partners': partners_data
        }

    @http.route('/partner/get_by_id', type="json", auth="public")
    def res_partner_get_by_id(self, id, **kwargs):
        partner = request.env['res.partner'].sudo().browse(int(id))
        return {
            'partner': {
                'id': partner.id,
                'name': partner.name,
                'company_name': partner.parent_name,
                'address': {
                    'street': partner.street,
                    'city': partner.city,
                    'zip': partner.zip,
                    'country': partner.country_id.name
                },
                'phone': partner.phone,
                'mobile': partner.mobile,
                'email': partner.email,
                'image': partner.image_128
            }
        }

    @http.route('/partner/create', type="json", auth="public")
    def res_partner_create(self, values, **kwargs):
        partner = request.env['res.partner'].sudo().create({
            'name': values['name'],
            'email': values['email']
        })

        return {
            'id': partner.id
        }

    @http.route('/lead/get_by_partner_id', type="json", auth="public")
    def crm_lead_get_by_partner_id(self, partner_id, **kwargs):
        partner_leads = request.env['crm.lead'].sudo().search([('partner_id', '=', partner_id)])
        leads = []
        for lead in partner_leads:
            leads.append({
                'name': lead.name,
                'expected_revenue': str(lead.expected_revenue),
                'planned_revenue': str(lead.planned_revenue),
                'currency_symbol': lead.company_currency.symbol
            })
        return {
            'leads': leads
        }

    @http.route('/lead/create', type="json", auth="public")
    def crm_lead_create(self, lead_values, **kwargs):
        lead = request.env['crm.lead'].sudo().create({
            'name': lead_values['name'],
            'partner_id': int(lead_values['partner_id']),
            'planned_revenue': int(lead_values['planned_revenue'])
        })

        return {
            'success': True if lead else False
        }
