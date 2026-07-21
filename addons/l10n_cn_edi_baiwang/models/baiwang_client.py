# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Baiwang EDI Client for Odoo (Thin Proxy Wrapper)

This module provides convenience methods that route all business calls through
the IAP proxy server. The proxy handles Baiwang credentials, OAuth tokens,
request signing, and API version management.

For development/testing, this can be swapped with a direct client that
talks to Baiwang without the proxy layer (see _legacy_direct_call comments).
"""

import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BaiwangClient:
    """
    Baiwang Open API client for e-Fapiao integration (Thin proxy wrapper).
    """

    def __init__(self, company):
        self.company = company
        self.tax_no = company.vat
        self.org_auth_code = company.l10n_cn_baiwang_org_auth_code
        self.proxy_user = company.l10n_cn_baiwang_proxy_user_id

    def _ensure_proxy_user(self):
        if not self.proxy_user:
            msg = self.company.env._(
                "Baiwang proxy user is not registered for this company. "
                "Please register it in Settings → Accounting → China Electronic Invoicing.",
            )
            raise UserError(msg)

    def issue_invoice(self, invoice_data: dict):
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_issue_invoice(self.company, invoice_data)
        if not result.get('success') and 'response' not in result:
            msg = self.company.env._("Baiwang proxy error: %s", result.get('error', 'Unknown error'))
            raise UserError(msg)
        return result.get('response', {})

    def query_invoice(self, query_data: dict):
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_query_invoice(self.company, query_data)
        if not result.get('success'):
            msg = self.company.env._("Baiwang invoice query failed: %s", result.get('error', 'Unknown error'))
            raise UserError(msg)
        return result.get('response', {})

    def add_red_confirmation(self, red_form_data: dict):
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_submit_red_form(self.company, red_form_data)
        if not result.get('success') and 'response' not in result:
            msg = self.company.env._("Baiwang red form submission failed: %s", result.get('error', 'Unknown error'))
            raise UserError(msg)
        return result.get('response', {})

    def operate_red_confirmation(self, red_confirm_uuid: str, red_confirm_no: str, confirm_type: str):
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_operate_red_form(
            self.company, red_confirm_uuid, red_confirm_no, confirm_type,
        )
        if not result.get('success'):
            msg = self.company.env._("Baiwang red form operation failed: %s", result.get('error', 'Unknown error'))
            raise UserError(msg)
        return result.get('response', {})

    def query_red_form_list(self, filters: dict | None = None):
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_poll_red_form_list(self.company, filters)
        if not result.get('success'):
            err = result.get('error') or result.get('response', {}).get('errorResponse', {}).get('message', 'Unknown API error')
            msg = self.company.env._("Baiwang red form list query failed: %s", err)
            raise UserError(msg)
        return result.get('response', {})

    def query_red_form_detail(self, red_confirm_uuid: str):
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_query_red_form(self.company, red_confirm_uuid)
        if not result.get('success'):
            msg = self.company.env._("Baiwang red form detail query failed: %s", result.get('error', 'Unknown error'))
            raise UserError(msg)
        return result.get('response', {})

    # --- Compatibility / Testing Methods ---

    def _get_token(self):
        """
        Stub for backward compatibility and credential testing.

        In the proxy architecture, token management is handled entirely on the IAP side.
        This method can be used for configuration validation (e.g., "Test Connection" button).

        Returns: 'OK' if proxy user is configured
        """
        self._ensure_proxy_user()
        return 'OK'

    def ensure_connection(self, timeout: float = 3.0):
        """Stub for backward compatibility. Not needed with proxy architecture."""
        self._ensure_proxy_user()
