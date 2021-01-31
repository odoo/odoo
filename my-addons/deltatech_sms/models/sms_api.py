# ©  2015-2019 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
#              Dan Stoica
# See README.rst file on addons root folder for license details

import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)


class SmsApi(models.AbstractModel):
    _inherit = "sms.api"

    @api.model
    def _contact_iap(self, local_endpoint, params):
        account = self.env["iap.account"].get("sms")
        # params['account_token'] = account.account_token
        # endpoint = self.env['ir.config_parameter'].sudo().get_param('sms.endpoint')

        res = []
        endpoint = self.env["ir.config_parameter"].sudo().get_param("sms.endpoint", "")
        for message in params["messages"]:

            endpoint = account.endpoint
            endpoint = endpoint.format(**message)

            result = requests.get(endpoint)
            response = result.content.decode("utf-8")
            res_value = {"state": "success", "res_id": message["res_id"]}
            if "OK" not in response:
                res_value["state"] = "server_error"
            res += [res_value]

        return res
