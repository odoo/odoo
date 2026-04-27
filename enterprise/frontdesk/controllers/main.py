# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, fields
from odoo.http import request
from odoo.tools import consteq

class Frontdesk(http.Controller):
    def _get_additional_info(self, frontdesk, lang, is_mobile=False):
        request.session.logout(keep_db=True)
        return request.render('frontdesk.frontdesk', {
            'frontdesk': frontdesk,
            'is_mobile': is_mobile,
            'current_lang': lang,
        })

    def _verify_token(self, frontdesk, token):
        if consteq(frontdesk.access_token, token):
            return True
        else:
            time_difference = fields.Datetime.now() - fields.Datetime.from_string(token[-19:])
            if time_difference.total_seconds() <= 3600 and consteq(frontdesk._get_tmp_code(), token[:64]):
                return True
            return False

    @http.route('/kiosk/<int:frontdesk_id>/<string:token>', type='http', auth='public', website=True)
    def launch_frontdesk(self, frontdesk_id, token, lang='en_US'):
        frontdesk = request.env['frontdesk.frontdesk'].sudo().browse(frontdesk_id)
        if not frontdesk.exists() or not self._verify_token(frontdesk, token):
            return request.not_found()
        return self._get_additional_info(frontdesk, lang)

    @http.route('/kiosk/<int:frontdesk_id>/mobile/<string:token>', type='http', auth='public', website=True)
    def launch_frontdesk_mobile(self, frontdesk_id, token, lang='en_US'):
        frontdesk = request.env['frontdesk.frontdesk'].sudo().browse(frontdesk_id)
        if not frontdesk.exists() or not self._verify_token(frontdesk, token):
            return request.render('frontdesk.frontdesk_qr_expired')
        return self._get_additional_info(frontdesk, lang, is_mobile=True)

    @http.route('/kiosk/<int:frontdesk_id>/get_tmp_code/<string:token>', type='json', auth='public')
    def get_tmp_code(self, frontdesk_id, token):
        frontdesk = request.env['frontdesk.frontdesk'].sudo().browse(frontdesk_id)
        if not frontdesk.exists() or not self._verify_token(frontdesk, token):
            return request.not_found()
        return (frontdesk._get_tmp_code(), fields.Datetime.to_string(fields.Datetime.now()))

    @http.route('/frontdesk/<int:frontdesk_id>/<string:token>/get_frontdesk_data', type='json', auth='public')
    def get_frontdesk_data(self, frontdesk_id, token):
        frontdesk = request.env['frontdesk.frontdesk'].sudo().browse(frontdesk_id)
        if not frontdesk.exists() or not self._verify_token(frontdesk, token):
            return request.not_found()
        return frontdesk._get_frontdesk_data()

    @http.route('/frontdesk/<int:frontdesk_id>/<string:token>/get_planned_visitors', type='json', auth='public')
    def get_planned_visitors(self, frontdesk_id, token):
        frontdesk = request.env['frontdesk.frontdesk'].sudo().browse(frontdesk_id)
        if not frontdesk.exists() or not self._verify_token(frontdesk, token):
            return request.not_found()
        return frontdesk._get_planned_visitors()

    @http.route('/frontdesk/<int:frontdesk_id>/background', type='http', auth='public')
    def frontdesk_background_image(self, frontdesk_id):
        frontdesk = request.env['frontdesk.frontdesk'].sudo().browse(frontdesk_id)
        if not frontdesk.image:
            return ""
        return request.env['ir.binary']._get_image_stream_from(frontdesk, 'image').get_response()

    @http.route('/frontdesk/<int:drink_id>/get_frontdesk_drinks', type='http', auth='public')
    def get_frontdesk_drinks(self, drink_id):
        drink = request.env['frontdesk.drink'].sudo().browse(drink_id)
        return request.env['ir.binary']._get_image_stream_from(drink, 'drink_image').get_response()

    @http.route('/frontdesk/<int:frontdesk_id>/<string:token>/get_hosts', type='json', auth='public')
    def get_hosts(self, frontdesk_id, token, name):
        frontdesk = request.env['frontdesk.frontdesk'].sudo().browse(frontdesk_id)
        if not frontdesk.exists() or not self._verify_token(frontdesk, token):
            return request.not_found()
        return request.env['hr.employee'].sudo().name_search(name, [('user_id', '!=', False), ('company_id', '=', frontdesk.company_id.id)])

    @http.route('/frontdesk/<int:frontdesk_id>/<string:token>/prepare_visitor_data', type='json', auth='public', methods=['POST'])
    def prepare_visitor_data(self, frontdesk_id, token, visitor_id=None, **kwargs):
        frontdesk = request.env['frontdesk.frontdesk'].sudo().browse(frontdesk_id)
        if not frontdesk.exists() or not self._verify_token(frontdesk, token):
            return request.not_found()
        visitor = request.env['frontdesk.visitor'].browse(visitor_id)
        vals = {'state': 'checked_in'}
        if visitor:
            if kwargs.get('drink_ids'):
                visitor_sudo = visitor.sudo()
                visitor_sudo.write({'drink_ids': [(4, drink_id) for drink_id in kwargs.get('drink_ids')]})
                return visitor_sudo._notify_to_people()
            return visitor.sudo().write(vals)
        else:
            vals.update({
                'station_id': frontdesk.id,
                'name': kwargs.get('name'),
                'phone': kwargs.get('phone'),
                'email': kwargs.get('email'),
                'check_in': fields.Datetime.now(),
                'company': kwargs.get('company'),
                'host_ids': [(4, host_id) for host_id in kwargs.get('host_ids')],
            })
            visitor = request.env['frontdesk.visitor'].sudo().create(vals)
            visitor._notify()
            return {'visitor_id': visitor.id}
