# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import requests
import pytz
from urllib.parse import urljoin

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

QRIS_TIMEOUT = 35  # They say that the time to get a response vary between 6 to 30s


def _l10n_id_make_qris_request(endpoint, params):
    """ Make an API request to QRIS, using the given path and params. """
    url = urljoin('https://qris.online/restapi/qris/', endpoint)
    try:
        response = requests.get(url, params=params, timeout=QRIS_TIMEOUT)
        response.raise_for_status()
        response = response.json()
    except requests.exceptions.HTTPError as err:
        raise ValidationError(_("Communication with QRIS failed. QRIS returned with the following error: %s", err))
    except (requests.RequestException, ValueError):
        raise ValidationError(_("Could not establish a connection to the QRIS API."))

    return response


class ResBank(models.Model):
    _inherit = "res.partner.bank"

    l10n_id_qris_api_key = fields.Char("QRIS API Key", groups="base.group_system")
    l10n_id_qris_mid = fields.Char("QRIS Merchant ID", groups="base.group_system")

    @api.model
    def _get_available_qr_methods(self):
        # EXTENDS account
        rslt = super()._get_available_qr_methods()
        rslt.append(('id_qr', _("QRIS"), 40))
        return rslt

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        # EXTENDS account
        if qr_method == 'id_qr':
            if self.country_code != 'ID':
                return _("You cannot generate a QRIS QR code with a bank account that is not in Indonesia.")
            if currency.name not in ['IDR']:
                return _("You cannot generate a QRIS QR code with a currency other than IDR")
            if not (self.sudo().l10n_id_qris_api_key and self.sudo().l10n_id_qris_mid):
                return _("To use QRIS QR code, Please setup the QRIS API Key and Merchant ID on the bank's configuration")
            return None

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'id_qr':
            if not amount:
                return _("The amount must be set to generate a QR code.")

        return super()._check_for_qr_code_errors(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        """ Getting content for the QR through calling QRIS API and storing the QRIS transaction as a record"""
        # EXTENDS account
        if qr_method == "id_qr":
            model = self._context.get('qris_model')
            model_id = self._context.get('qris_model_id')

            # qris_trx is to help us fetch the backend record associated to the model and model_id.
            # we are using model and model_id instead of model.browse(id) because while executing this method
            # not all backend records are created already. For example, pos.order record isn't created until
            # payment is completed on the PoS interace.
            qris_trx = self.env['l10n_id.qris.transaction']._get_latest_transaction(model, model_id)

            # QRIS codes are valid for 30 minutes. To leave some margin, we will return the same QR code we already
            # generated if the invoice is re-accessed before 25m. Otherwise, a new QR code is generated
            # Additionally, we want to check that it's requesting for the same amount as it's possible to change
            # amount in apps like PoS.
            if qris_trx and qris_trx.qris_amount == int(amount):
                now = fields.Datetime.now()
                latest_qr_date = qris_trx.qris_creation_datetime

                if (now - latest_qr_date).total_seconds() < 1500:
                    return qris_trx['qris_content']

            params = {
                "do": "create-invoice",
                "apikey": self.l10n_id_qris_api_key,
                "mID": self.l10n_id_qris_mid,
                "cliTrxNumber": structured_communication,
                "cliTrxAmount": int(amount)
            }
            response = _l10n_id_make_qris_request('show_qris.php', params)
            if response.get("status") == "failed":
                raise ValidationError(response.get("data"))
            data = response.get('data')

            # create a new transaction line while also converting the qris_request_date to UTC time
            if model and model_id:
                new_trx = self.env['l10n_id.qris.transaction'].create({
                    'model': model,
                    'model_id': model_id,
                    'qris_invoice_id': data.get('qris_invoiceid'),
                    'qris_amount': int(amount),
                    # Since the QRIS response is always returned with "Asia/Jakarta" timezone which is UTC+07:00
                    'qris_creation_datetime': fields.Datetime.to_datetime(data.get('qris_request_date')) - datetime.timedelta(hours=7),
                    'qris_content': data.get('qris_content'),
                    'bank_id': self.id
                })

                # Search the backend record and attach the qris transaction to the record if it exists.
                trx_record = new_trx._get_record()
                if trx_record:
                    trx_record.l10n_id_qris_transaction_ids |= new_trx

            return data.get('qris_content')

        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        # EXTENDS account
        if qr_method == 'id_qr':
            if not self._context.get('is_online_qr'):
                return {}
            return {
                'barcode_type': 'QR',
                'width': 120,
                'height': 120,
                'value': self._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication),
            }
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _l10n_id_qris_fetch_status(self, qr_data):
        """
        using self and the given data, fetches the status of a specific QR code generated by QRIS
        Expected values in the qr_data dict are:
            - invoice_id returned when generating a QR code
            - the amount present in the qr code
            - the datetime at which the QR code was generated
        """
        return _l10n_id_make_qris_request('checkpaid_qris.php', {
            'do': 'checkStatus',
            'apikey': self.l10n_id_qris_api_key,
            'mID': self.l10n_id_qris_mid,
            'invid': qr_data['qris_invoice_id'],
            'trxvalue': qr_data['qris_amount'],
            'trxdate': qr_data['qris_creation_datetime'],
        })
