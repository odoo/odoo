import base64
from hashlib import sha256

import requests

from odoo.exceptions import UserError

from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService


class KSeFTimeoutError(UserError):
    pass


class KsefOfflineApiService(KsefApiService):

    _sending_offline_invoice = False

    def _make_request(self, method, endpoint, is_auth_retry=False, **kwargs):
        if self._sending_offline_invoice:
            kwargs['json']['offlineMode'] = True
        try:
            return super()._make_request(
                method, endpoint, is_auth_retry=is_auth_retry, **kwargs,
            )
        except UserError as error:
            if isinstance(error.__context__, requests.exceptions.Timeout):
                raise KSeFTimeoutError(self.env._("The KSeF request timed out.")) from error.__context__
            raise

    @staticmethod
    def get_invoice_hash(xml_content_bytes):
        return base64.b64encode(sha256(xml_content_bytes).digest()).decode()

    def send_offline_invoice(self, xml_content_bytes):
        self._sending_offline_invoice = True
        try:
            return super().send_invoice(xml_content_bytes)
        finally:
            self._sending_offline_invoice = False

    def _get_session_invoices(self, session_id, continuation_token=None):
        headers = {'x-continuation-token': continuation_token} if continuation_token else {}
        return self._make_request(
            'GET',
            f"{self.api_url}/sessions/{session_id}/invoices",
            params={'pageSize': 1000},
            headers=headers,
        ).json()

    def find_invoice_in_session(self, invoice_hash, session_id):
        continuation_token = None
        matching_invoice = None
        while True:
            response = self._get_session_invoices(session_id, continuation_token)
            for invoice in response.get('invoices', []):
                if invoice.get('invoiceHash') == invoice_hash:
                    matching_invoice = invoice
            continuation_token = response.get('continuationToken')
            if not continuation_token:
                return matching_invoice
