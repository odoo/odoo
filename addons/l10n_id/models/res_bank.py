# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

QRIS_API_URL = "https://qris.online/restapi/qris/show_qris.php"

class ResBank(models.Model):
    _inherit = "res.partner.bank"

    l10n_id_qris_api_key = fields.Char("QRIS API Key", groups="base.group_system")
    l10n_id_qris_mid = fields.Char("QRIS Merchant ID", groups="base.group_system")

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        rslt.append(('id_qr', _("QRIS"), 40))
        return rslt

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == 'id_qr' and self.country_code == 'ID':
            if currency.name not in ['IDR']:
                return _("You cannot generate a QRIS QR code with a currency other than IDR")
            if not (self.l10n_id_qris_api_key and self.l10n_id_qris_mid):
                return _("To use QRIS QR code, Please setup the QRIS API Key and Merchant ID on the bank's configuration")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        """Override

        Getting content for the QR through calling QRIS API"""
        if qr_method == "id_qr":
            params = {
                "do": "create-invoice",
                "apikey": self.l10n_id_qris_api_key,
                "mID": self.l10n_id_qris_mid,
                "cliTrxNumber": structured_communication,
                "cliTrxAmount": int(amount)
            }
            try:
                res = requests.get(QRIS_API_URL, params=params, timeout=10)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                raise ValidationError(_("Could not establish a connection to the QRIS API."))
            except requests.exceptions.HTTPError as err:
                raise ValidationError(_("Communication with QRIS failed. QRIS returned with the following error: %s", err))

            response = res.json()
            if response.get('status') == 'failed':
                err_msg = response.get('data')
                raise ValidationError(_("Communication with QRIS failed. QRIS returned with the following error: %s", err_msg))
            qris_content = response.get("data").get("qris_content")
            return qris_content

        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'id_qr':
            if not self._context.get('from_portal'):
                return {}
            return {
                'barcode_type': 'QR',
                'width': 120,
                'height': 120,
                'value': self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication),
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)
