# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import Controller, route, request
import uuid
import json

from werkzeug.exceptions import Forbidden, BadRequest


class Referral(Controller):

    @route(['/referral'], type='http', auth='public', website=True)
    def referral_unauth(self, force=False, **kwargs):
        if not force and not request.website.is_public_user():
            if request.env.user.partner_id.referral_tracking_id:
                token = request.env.user.partner_id.referral_tracking_id.token
                return request.redirect('/referral/' + token)
            else:
                return self.referral_register(request.env.user.partner_id.email)
        else:
            return request.render('website_sale_referral.referral_controller_template_register')

    @route(['/referral/register'], type='http', auth='public', method='POST', website=True)
    def referral_register(self, referrer_email, token=None, **post):
        if token:
            referral_tracking = request.env['referral.tracking'].search([('token', '=', token)], limit=1)
            if referral_tracking:
                if referral_tracking.referrer_email != referrer_email:
                    raise Forbidden()  # Mismatch between email and token
                else:
                    return request.redirect('/referral/' + referral_tracking.token)
        else:
            existing_token = True
            while(existing_token):  # check that this token doesn't already exists
                token = uuid.uuid4().hex[:-1]  # to avoid conflict with saas token
                existing_token = request.env['referral.tracking'].search([('token', '=', token)], limit=1)

        utm_name = ('%s-%s') % (referrer_email, str(uuid.uuid4())[:6])
        utm_source_id = request.env['utm.source'].sudo().create({'name': utm_name})
        referral_tracking = request.env['referral.tracking'].sudo().create({
            'token': token,
            'utm_source_id': utm_source_id.id,
            'referrer_email': referrer_email,
        })
        if not request.website.is_public_user() and referrer_email == request.env.user.partner_id.email:
            request.env.user.partner_id.update({'referral_tracking_id': referral_tracking.id})
        return request.redirect('/referral/' + referral_tracking.token)

    @route(['/referral/<string:token>'], type='http', auth='public', website=True)
    def referral(self, token, **post):
        referral_tracking = request.env['referral.tracking'].search([('token', '=', token)], limit=1)
        if not referral_tracking:
            return request.not_found()  # incorrect token

        return request.render('website_sale_referral.referral_controller_template', {
            'token': token,
            'referrer_email': referral_tracking.referrer_email,
        })

    @route(['/referral/tracking/<string:token>', '/referral/tracking'], type='json', auth='public', website=True)
    def referral_tracking(self, token=None, **kwargs):
        reward_value = request.env['ir.config_parameter'].sudo().get_param('website_sale_referral.reward_value')
        currency_id = request.env.user.company_id.currency_id

        if not token:
            return {
                'currency_position': currency_id.position,
                'currency_symbol': currency_id.symbol,
                'reward_value': reward_value,
            }

        referral_tracking = request.env['referral.tracking'].search([('token', '=', token)], limit=1)
        if not referral_tracking:
            return request.not_found()  # incorrect token
        my_referrals = self._get_referral_infos(referral_tracking.sudo().utm_source_id)

        return {
            'currency_position': currency_id.position,
            'currency_symbol': currency_id.symbol,
            'reward_value': reward_value,
            'my_referrals': my_referrals,
        }

    @route(['/referral/send'], type='json', auth='public', method='POST', website=True)
    def referral_send(self, token, **post):
        link_tracker = request.env['link.tracker'].sudo().create({
            'url': request.env['ir.config_parameter'].sudo().get_param('website_sale_referral.redirect_page') or request.env["ir.config_parameter"].sudo().get_param("web.base.url"),
            'campaign_id': request.env.ref('website_sale_referral.utm_campaign_referral').id,
            'source_id': self._get_utm_source_id(token),
            'medium_id': request.env.ref('utm.utm_medium_%s' % post.get('channel')).id
        })

        return {'link': self._get_link_tracker_url(link_tracker, post.get('channel'))}

    def _get_utm_source_id(self, token):
        referral_tracking = request.env['referral.tracking'].search([('token', '=', token)], limit=1)
        if not referral_tracking:
            return BadRequest("Token doesn't exist")
        return referral_tracking.sudo().utm_source_id.id

    def _get_referral_infos(self, utm_source_id):
        return request.env['sale.order'].sudo()._get_referral_infos(utm_source_id)

    def _get_link_tracker_url(self, link_tracker, channel):
        if channel == 'direct':
            return link_tracker.short_url
        if channel == 'facebook':
            return 'https://www.facebook.com/sharer/sharer.php?u=%s' % link_tracker.short_url
        elif channel == 'twitter':
            twitter = request.env['ir.config_parameter'].sudo().get_param('website_sale_referral.twitter_message') or ''
            return 'https://twitter.com/intent/tweet?tw_p=tweetbutton&text=%s %s' % (twitter, link_tracker.short_url)
        elif channel == 'linkedin':
            return 'https://www.linkedin.com/shareArticle?mini=true&url=%s' % link_tracker.short_url
