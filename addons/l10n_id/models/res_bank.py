# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
            if not (self.l10n_id_qris_api_key and self.l10n_id_qris_mid):
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
        """ Getting content for the QR through calling QRIS API """
        # EXTENDS account
        if qr_method == "id_qr":
            invoice = self.env['account.move'].browse(self._context.get('qris_originating_invoice_id'))

            # QRIS codes are valid for 30 minutes. To leave some margin, we will return the same QR code we already
            # generated if the invoice is re-accessed before 25m. Otherwise, a new QR code is generated.
            if invoice and invoice.l10n_id_qris_invoice_details:
                now = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Jakarta'), fields.Datetime.now())
                # We need it to be tz aware for the comparison below.
                latest_qr_date = fields.Datetime.to_datetime(
                    invoice.l10n_id_qris_invoice_details[-1]['qris_creation_datetime']
                ).replace(tzinfo=pytz.timezone('Asia/Jakarta'))

                if invoice and (now - latest_qr_date).total_seconds() < 1500:
                    return invoice.l10n_id_qris_invoice_details[-1]['qris_content']

            params = {
                "do": "create-invoice",
                "apikey": self.l10n_id_qris_api_key,
                "mID": self.l10n_id_qris_mid,
                "cliTrxNumber": structured_communication,
                "cliTrxAmount": int(amount)
            }
            response = _l10n_id_make_qris_request('show_qris.php', params)
            data = response.get('data')

            # if the invoice is available, we will write the QR information on it to allow fetching payment information later on.
            if invoice:
                # it's a bit far-fetched, but let's imagine the qr was generated 27m ago by a user A, and then user B check the invoice
                # it would regenerate a new QR code, but user A could have been paid the first one.
                # To that end, we will store the id and date of all generated qr codes, and only discard them later on when checking the status.
                qris_invoice_details = invoice.l10n_id_qris_invoice_details or []
                qris_invoice_details.append({
                    'qris_invoice_id': data.get('qris_invoiceid'),
                    'qris_amount': int(amount),
                    'qris_creation_datetime': data.get('qris_request_date'),  # need to convert timezone to UTC to store
                    'qris_content': data.get('qris_content'),
                })
                invoice.l10n_id_qris_invoice_details = qris_invoice_details

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
