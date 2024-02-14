# coding: utf-8

import requests
import time
import json
import base64
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class PosOnlineDeliveryProvider(models.Model):
    _inherit = 'pos.online.delivery.provider'

    webhook_secret = fields.Char('Webhook Secret', copy=False)
    site_id = fields.Integer('Site Location ID', copy=False)
    code = fields.Selection(selection_add=[('deliveroo', "Deliveroo")], ondelete={'deliveroo': 'set default'})
    busy_time = fields.Integer('Busy Time')
    quiet_time = fields.Integer('Quiet Time')

    def write(self, vals):
        if vals.get('busy_time') or vals.get('quiet_time'):
            response = self._set_site_workload_time(vals.get('quiet_time', self.quiet_time), vals.get('busy_time', self.busy_time))
            if response:
                self.quiet_time = response.get('quiet')
                self.busy_time = response.get('busy')
        return super().write(vals)

    @api.onchange('state')
    def _onchange_state(self):
        super()._onchange_state()
        if self.code == 'deliveroo' and self.state in ('enabled', 'test'):
            if not self.webhook_secret:
                raise ValidationError(_('Please fill in the webhook secret provided by Deliveroo.'))
            if not self.site_id:
                raise ValidationError(_('Please fill in the site location ID provided by Deliveroo.'))
            
    def _get_delivery_acceptation_time(self):
        res = super()._get_delivery_acceptation_time()
        if self.code == "deliveroo":
            if self.env.company.country_code in ['KW', 'AE']:
                return 7
            return 10
        return res
    
    def _get_api_url(self, suffix: str):
        if self.code == "deliveroo":
            if self.state == "enabled":
                return "https://api.developers.deliveroo.com" + suffix
            if self.state == "test":
                return "https://api-sandbox.developers.deliveroo.com" + suffix
        return super()._get_api_url()
            
    #ORDERS API

    def _accept_order(self, id: int, status: str = ""):
        """
        used for tablet-less flow
        """
        if not status:
            status = "accepted"
        response = requests.patch(
            self._get_api_url(f"/order/v1/orders/{id}"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={"status": status},
        )
        return response.status_code == 204

    def _reject_order(self, id: int, rejected_reason: str = "busy"):
        """
        used for tablet-less flow
        the rejected reason can be ["busy", "closing_early", "ingredient_unavailable", "other"]
        """
        response = requests.patch(
            self._get_api_url(f"/order/v1/orders/{id}"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={
                "status": "rejected",
                "reject_reason": rejected_reason,
            },
        )
        return response.status_code == 204

    def _confirm_accepted_order(self, id: int):
        """
        used for tablet-less flow
        """
        response = requests.patch(
            self._get_api_url(f"/order/v1/orders/{id}"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={
                "status": "confirmed",
            },
        )
        return response.status_code == 204

    def _send_preparation_status(self, id: int, stage: str, delay: int = 0):
        if stage in ['in_kitchen', 'ready_for_collection_soon', 'ready_for_collection', 'collected']:
            json = {
                'stage': stage,
                'occurred_at': str(datetime.utcnow().replace(microsecond=0).isoformat()) + 'Z'
            }
            if stage == 'in_kitchen'and delay in [0, 2, 4, 6, 10]:
                json['delay'] = delay
            response = requests.post(
                self._get_api_url(f"/order/v1/orders/{id}/prep_stage"),
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                    "Authorization": f"Bearer {self._get_access_token()}",
                },
                json=json,
            )
            return response.status_code == 200
        return False
    
    #AUTHENTIFICATION API

    def _refresh_access_token(self) -> str:
        self.ensure_one()
        if self.code != "deliveroo":
            return super()._refresh_access_token()
        AUTH_HOST = 'https://auth-sandbox.developers.deliveroo.com/oauth2/token'
        # AUTH_HOST = 'https://auth.developers.deliveroo.com/oauth2/token'

        # Encode client_id:client_secret in base64
        auth_string = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        # Data for the request
        data = {
            'grant_type': 'client_credentials'
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {auth_string}'
        }

        # Make the POST request
        response = requests.post(AUTH_HOST, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.access_token_expiration_timestamp = time.time() + token_data.get(
                "expires_in"
            )
            return token_data.get("access_token")
        return False
    
    #MENU API

    def action_upload_menu(self):
        if self.code == "deliveroo" and self.state == "disabled":
            self._upload_menu('test menu', json.dumps({'test': 'test'}))
        else:
            raise UserError(_("You cannot update the menu of a disabled provider."))

    def _upload_menu(self, name, menu):
        # TODO: implement sending menu to deliveroo
        if self.code == 'deliveroo':
            response = requests.put(
                self._get_api_url(f"/menu/v1/brands/{self._get_brand_id()}/menus/{self.menu_id}"),
                headers={
                    "accept": "application/json",
                    'content-type': 'application/json',
                    "Authorization": f"Bearer {self._get_access_token()}",
                },
                json={
                    'name': name,
                    'menu': menu,
                    'site_ids': [self.site_id],
                }
            )
        else:
            return super()._upload_menu()

    #SITE API
    def _get_brand_id(self):
        if self.brand_id:
            return self.brand_id
        response = requests.get(
            self._get_api_url(f"/site/v1/restaurant_locations/{self.site_id}"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        if response.status_code == 200:
            self.brand_id = response.json().get("brand_id")
            return self.brand_id
        return False
    
    def _get_site_status(self):
        response = requests.get(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/status"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return response.json().get('status') if response.status_code == 200 else False

    def _change_site_status_mode(self, status):
        #send to deliveroo the information about the restaurant status [open, closed, ready_to_open]
        if status not in ['OPEN', 'CLOSED', 'READY_TO_OPEN']:
            return False
        if self._get_site_status(self) == status:
            return True
        response = requests.put(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/status"),
            headers={
                "accept": "application/json",
                'content-type': 'application/json',
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json = {
                'status': status,
            },
        )
        return response.status_code == 200
    
    def _get_site_workload_mode(self):
        response = requests.get(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/workload/mode"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return response.json().get('mode') if response.status_code == 200 else False
    
    def _set_site_workload_mode(self, mode):
        if mode not in ['BUSY', 'QUIET']:
            return False
        if self._get_site_workload_mode() == mode:
            return True
        response = requests.put(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/workload/mode"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return response.json().get('mode') if response.status_code == 200 else False
    
    def _set_site_workload_time(self, quiet_time, busy_time):
        response = requests.put(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/workload/times"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json = {
                'quite': quiet_time,
                'busy': busy_time,
            },
        )
        return response.json() if response.status_code == 200 else False

    def _get_site_brand_id(self):
        response = requests.get(
            self._get_api_url(f"/site/v1/restaurant_locations/{self.site_id}"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return json.loads(response.content) if response.status_code == 200 else False
    
    def _get_site_opening_hours(self):
        response = requests.get(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/opening_hours"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return response.json() if response.status_code == 200 else False
    
    def _update_site_opening_hours(self, opening_hours):
        response = requests.post(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/opening_hours"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={
                'opening_hours': opening_hours,
            }
        )
        return response.json() if response.status_code == 200 else False
