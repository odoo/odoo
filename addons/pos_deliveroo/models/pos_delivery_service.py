# coding: utf-8

import requests
import time

from odoo import fields, models, api
import datetime

class PosDeliveryService(models.Model):
    _inherit = "pos.delivery.service"

    webhook_secret = fields.Char("Webhook Secret", copy=False)


    def _get_available_services(self):
        return super()._get_available_services() + [("deliveroo", "Deliveroo")]

    @api.model
    def _accept_order(self, id: int):
        """
        used for tablet-less flow
        """
        response = requests.patch(
            f"https://api{'-sandbox' if self.is_test else ''}.developers.deliveroo.com/order/v1/orders/{id}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={"status": "accepted"},
        )
        return response.status_code == 204

    @api.model
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

    @api.model
    def _refresh_access_token(self) -> str:
        self.ensure_one()
        if self.service != "deliveroo":
            return super()._refresh_access_token()
        response = requests.post(
            f"https://auth{'-sandbox' if self.is_test else ''}.developers.deliveroo.com/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
        )
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.access_token_expiration_timestamp = time.time() + token_data.get(
                "expires_in"
            )
            return token_data.get("access_token")

    @api.model
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
