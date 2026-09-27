import json
import requests

from odoo import _


class ETAClient:
    """Client for the Egyptian Tax Authority API."""

    ETA_DOMAINS = {
        'preproduction': 'https://api.preprod.invoicing.eta.gov.eg',
        'production': 'https://api.invoicing.eta.gov.eg',
        'invoice.preproduction': 'https://preprod.invoicing.eta.gov.eg',
        'invoice.production': 'https://invoicing.eta.gov.eg',
        'token.preproduction': 'https://id.preprod.eta.gov.eg',
        'token.production': 'https://id.eta.gov.eg',
    }

    def __init__(self, is_production):
        self.is_production = is_production

    def get_access_token(self, body, headers):
        return self._request(
            self.token_domain,
            '/connect/token',
            'POST',
            body=body,
            headers=headers,
        )

    def submit_invoices(self, body, headers):
        return self._request(
            self.api_domain,
            '/api/v1.0/documentsubmissions',
            'POST',
            body=body,
            headers=headers,
        )

    def get_invoice_pdf(self, uuid, headers):
        return self._request(
            self.api_domain,
            f'/api/v1.0/documents/{uuid}/pdf',
            'GET',
            headers=headers,
        )

    def cancel_invoice(self, uuid, body, headers):
        return self._request(
            self.api_domain,
            f'/api/v1.0/documents/state/{uuid}/state',
            'PUT',
            body=body,
            headers=headers,
        )

    def get_invoice_url(self, uuid, long_id):
        return f'{self.invoice_domain}/documents/{uuid}/share/{long_id}'

    def submit_receipt(self, body, headers):
        return self._request(
            self.api_domain,
            '/api/v1/receiptsubmissions',
            'POST',
            body=body,
            headers=headers,
        )

    def get_receipt_url(self, uuid, date_order, amount_total, seller_rin):
        return f'{self.invoice_domain}/receipts/search/{uuid}/share/{date_order}#Total:{amount_total},IssuerRIN:{seller_rin}'

    @property
    def api_domain(self):
        return self.ETA_DOMAINS[
            'production' if self.is_production else 'preproduction'
        ]

    @property
    def token_domain(self):
        return self.ETA_DOMAINS[
            'token.production' if self.is_production else 'token.preproduction'
        ]

    @property
    def invoice_domain(self):
        return self.ETA_DOMAINS[
            'invoice.production' if self.is_production else 'invoice.preproduction'
        ]

    def _request(
        self,
        domain,
        url,
        method,
        body=None,
        headers=None,
    ):
        request_url = domain + url
        timeout = (20, 40) if '/pdf' in url else 20

        try:
            response = requests.request(
                method,
                request_url,
                data=body,
                headers=headers,
                timeout=timeout,
            )
        except requests.exceptions.MissingSchema:
            return self._parse_error(
                _("Invalid URL schema. Please check the URL and try again."),
            )
        except requests.exceptions.ConnectionError:
            return self._parse_error(
                _("Failed to connect to ETA. Please try again later."),
            )
        except requests.exceptions.Timeout:
            return self._parse_error(
                _("Request to ETA timed out. Please try again later"),
            )

        return response.content

    @staticmethod
    def _parse_error(message):
        return json.dumps({
            'error': {
                'code': '000',
                'message': message,
            },
        })
