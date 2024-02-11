# coding: utf-8

import requests
import time
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import datetime

class PosOnlineDeliveryProvider(models.Model):
    _inherit = 'pos.online.delivery.provider'

    webhook_secret = fields.Char('Webhook Secret', copy=False)
    code = fields.Selection(selection_add=[('deliveroo', "Deliveroo")], ondelete={'deliveroo': 'set default'})

    @api.onchange('state')
    def _onchange_state(self):
        super()._onchange_state()
        if self.code == 'deliveroo' and self.state in ('enabled', 'test'):
            if not self.webhook_secret:
                raise ValidationError(_('Please fill in the webhook secret provided by Deliveroo.'))

    def _accept_order(self, id: int, status: str = ""):
        """
        used for tablet-less flow
        """
        if not status:
            status = "accepted"
        response = requests.patch(
            f"https://api-sandbox.developers.deliveroo.com/order/v1/orders/{id}",
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
            f"https://api-sandbox.developers.deliveroo.com/order/v1/orders/{id}",
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
            f"https://api-sandbox.developers.deliveroo.com/order/v1/orders/{id}",
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

    def _send_sync_status(self, id: int, positive=True):
        """
        used for tablet flow
        """
        response = requests.post(
            f"https://api{'-sandbox' if self.is_test else ''}.developers.deliveroo.com/order/v1/orders/{id}/sync_status",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
                "Accept": "application/json",
            },
            json={
                "status": "succeeded",
                "occurred_at": datetime.datetime.now().isoformat(),
            },
        )
        return response.json()

    def _refresh_access_token(self) -> str:
        import base64
        self.ensure_one()
        if self.code != "deliveroo":
            return super()._refresh_access_token()

        AUTH_HOST = 'https://auth-sandbox.developers.deliveroo.com/oauth2/token'

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

    def _upload_menu(self):
        self.ensure_one()
        # example
        # TODO: implement
        menu = {
            "name": "My Menu",
            "description": "My Menu Description",
            "items": [
                {
                    **product_id.read([]),
                }
                for product_id in self.env["product.product"].search([])
            ],
        }
        # TODO: implement sending menu to deliveroo

    def _get_delivery_acceptation_time(self):
        res = super()._get_delivery_acceptation_time()
        if self.code == "deliveroo":
            if self.env.company.country_code in ['KW', 'AE']:
                return 7
            return 10
        return res