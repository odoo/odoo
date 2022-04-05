# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.http import request


class MailingSMSController(http.Controller):

    def _check_trace(self, mailing_id, trace_code):
        try:
            mailing = request.env['mailing.mailing'].sudo().search([('id', '=', mailing_id)])
        except:
            mailing = False
        if not mailing:
            return {'error': 'mailing_error'}
        trace = request.env['mailing.trace'].sudo().search([
            ('trace_type', '=', 'sms'),
            ('sms_code', '=', trace_code),
            ('mass_mailing_id', '=', mailing.id)
        ])
        if not trace:
            return {'error': 'trace_error'}
        return {'trace': trace}

    @http.route(['/sms/<int:mailing_id>/<string:trace_code>'], type='http', website=True, auth='public')
    def blacklist_page(self, mailing_id, trace_code, **post):
        check_res = self._check_trace(mailing_id, trace_code)
        if not check_res.get('trace'):
            return request.redirect('/web')
        return request.render('mass_mailing_sms.blacklist_main', {
            'mailing_id': mailing_id,
            'trace_code': trace_code,
        })

    @http.route(['/sms/<int:mailing_id>/unsubscribe/<string:trace_code>'], type='http', website=True, auth='public')
    def blacklist_number(self, mailing_id, trace_code, **post):
        check_res = self._check_trace(mailing_id, trace_code)
        if not check_res.get('trace'):
            return request.redirect('/web')
        country_code = request.geoip.get('country_code')
        # parse and validate number
        sms_number = post.get('sms_number', '').strip(' ')
        sanitize_res = phone_validation.phone_sanitize_numbers([sms_number], country_code, None)[sms_number]
        tocheck_number = sanitize_res['sanitized'] or sms_number

        trace = check_res['trace'].filtered(lambda r: r.sms_number == tocheck_number)[:1]
        mailing_list_ids = trace.mass_mailing_id.contact_list_ids

        # compute opt-out / blacklist information
        lists_optout = request.env['mailing.list'].sudo()
        lists_optin = request.env['mailing.list'].sudo()
        unsubscribe_error = False
        if tocheck_number and trace:
            if mailing_list_ids:
                subscriptions = request.env['mailing.contact.subscription'].sudo().search([
                    ('list_id', 'in', mailing_list_ids.ids),
                    ('contact_id.phone_sanitized', '=', tocheck_number),
                ])
                subscriptions.write({'opt_out': True})
                lists_optout = subscriptions.mapped('list_id')
            else:
                blacklist_rec = request.env['phone.blacklist'].sudo().add(tocheck_number)
                blacklist_rec._message_log(
                    body=_('Blacklist through SMS Marketing unsubscribe (mailing ID: %s - model: %s)') %
                          (trace.mass_mailing_id.id, trace.mass_mailing_id.mailing_model_id.display_name))
            lists_optin = request.env['mailing.contact.subscription'].sudo().search([
                ('contact_id.phone_sanitized', '=', tocheck_number),
                ('list_id', 'not in', mailing_list_ids.ids),
                ('opt_out', '=', False),
            ]).mapped('list_id')
        elif tocheck_number:
            unsubscribe_error = _('Number %s not found', tocheck_number)
        else:
            unsubscribe_error = sanitize_res['msg']

        return request.render('mass_mailing_sms.blacklist_number', {
            'mailing_id': mailing_id,
            'trace_code': trace_code,
            'sms_number': sms_number,
            'lists_optin': lists_optin,
            'lists_optout': lists_optout,
            'unsubscribe_error': unsubscribe_error,
        })

    @http.route('/r/<string:code>/s/<int:sms_sms_id>', type='http', auth="public")
    def sms_short_link_redirect(self, code, sms_sms_id, **post):
        country_code = request.geoip.get('country_code')
        if sms_sms_id:
            trace_id = request.env['mailing.trace'].sudo().search([('sms_sms_id_int', '=', int(sms_sms_id))]).id
        else:
            trace_id = False

        request.env['link.tracker.click'].sudo().add_click(
            code,
            ip=request.httprequest.remote_addr,
            country_code=country_code,
            mailing_trace_id=trace_id
        )
        return request.redirect(request.env['link.tracker'].get_url_from_code(code), code=301, local=False)
