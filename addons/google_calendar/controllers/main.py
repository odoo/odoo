# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_account.controllers.main import GoogleAuth
import json
import requests
from werkzeug.exceptions import BadRequest


class GoogleCalendarController(http.Controller):

    @http.route('/google_calendar/sync_data', type='json', auth='user')
    def sync_data(self, model, **kw):
        """ This route/function is called when we want to synchronize Odoo
            calendar with Google Calendar.
            Function return a dictionary with the status :  need_config_from_admin, need_auth,
            need_refresh, sync_stopped, success if not calendar_event
            The dictionary may contains an url, to allow Odoo Client to redirect user on
            this URL for authorization for example
        """
        if model == 'calendar.event':
            base_url = request.httprequest.url_root.strip('/')
            GoogleCal = GoogleCalendarService(request.env['google.service'].with_context(base_url=base_url))

            # Checking that admin have already configured Google API for google synchronization !
            client_id = request.env['google.service']._get_client_id('calendar')

            if not client_id or client_id == '':
                action_id = ''
                if GoogleCal._can_authorize_google(request.env.user):
                    action_id = request.env.ref('base_setup.action_general_configuration').id
                return {
                    "status": "need_config_from_admin",
                    "url": '',
                    "action": action_id
                }

            # Checking that user have already accepted Odoo to access his calendar !
            if not GoogleCal.is_authorized(request.env.user):
                url = GoogleCal._google_authentication_url(from_url=kw.get('fromurl'))
                return {
                    "status": "need_auth",
                    "url": url
                }
            # If App authorized, and user access accepted, We launch the synchronization
            need_refresh = request.env.user.sudo()._sync_google_calendar(GoogleCal, no_sync_to_google=True)

            # If synchronization has been stopped
            if not need_refresh and request.env.user.google_synchronization_stopped:
                return {
                    "status": "sync_stopped",
                    "url": ''
                }
            return {
                "status": "need_refresh" if need_refresh else "no_new_event_from_google",
                "url": ''
            }

        return {"status": "success"}


class GoogleCalendarAuth(GoogleAuth):

    @http.route('/google_account/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        """ This route/function is called by Google when user Accept/Refuse the consent of Google """
        state = json.loads(kw.get('state', '{}'))
        service = state.get('s')
        url_return = state.get('f')
        if (not service or (kw.get('code') and not url_return)):
            raise BadRequest()

        if kw.get('code'):
            base_url = request.httprequest.url_root.strip('/') or request.env.user.get_base_url()
            access_token, refresh_token, ttl = request.env['google.service']._get_google_tokens(
                kw['code'],
                service,
                redirect_uri=f'{base_url}/google_account/authentication'
            )
            if service == 'calendar' and access_token:
                try:
                    resp_token = requests.request(
                        method='POST',
                        url='https://www.googleapis.com/oauth2/v3/userinfo',
                        params={
                            'access_token': access_token
                        }).json()
                    email = resp_token.get('email')
                    if not email:
                        return request.redirect("%s%s%s" % (url_return, "?error=", 'Email Google not Found'))
                    if email != state.get('e'):
                        return request.redirect(
                            "%s%s%s" % (url_return, "?error=", 'Email is not Valid for Sync Google Calendar'))
                except Exception as e:
                    return request.redirect(
                        "%s%s%s" % (url_return, "?error=", 'Failed to Get Google Token -> %s' % str(e)))
            service_field = f'google_{service}_account_id'
            if service_field in request.env.user:
                getattr(request.env.user, service_field)._set_auth_tokens(access_token, refresh_token, ttl)
            else:
                raise Warning('No callback field for service <%s>' % service)
            return request.redirect(url_return)
        elif kw.get('error'):
            return request.redirect("%s%s%s" % (url_return, "?error=", kw['error']))
        else:
            return request.redirect("%s%s" % (url_return, "?error=Unknown_error"))
