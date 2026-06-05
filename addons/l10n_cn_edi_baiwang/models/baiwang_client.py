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

    All calls are routed through the IAP proxy server, which:
    - Manages Baiwang credentials securely (not stored in tenant DB)
    - Handles OAuth token retrieval and caching
    - Performs request signing
    - Manages API version wrapping (v6.0, v7.0)
    """

    def __init__(self, company):
        """
        Args:
            company: res.company instance
        """
        self.company = company
        self.tax_no = company.vat
        self.org_auth_code = company.l10n_cn_baiwang_org_auth_code
        self.proxy_user = company.l10n_cn_baiwang_proxy_user_id

    def _ensure_proxy_user(self):
        """Ensure proxy user is registered."""
        if not self.proxy_user:
            raise UserError(
                "Baiwang proxy user is not registered for this company. "
                "Please register it in Settings → Accounting → China Electronic Invoicing.",
            )

    # --- Public Business API Methods (via proxy) ---

    def issue_invoice(self, invoice_data: dict):
        """
        Issue a blue or red invoice (v6.0 with data wrapper).

        Args:
            invoice_data: The invoice business content (goes inside 'data' key)

        Returns:
            Dictionary with response from Baiwang
        """
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_issue_invoice(self.company, invoice_data)
        if not result.get('success'):
            raise UserError(
                f"Baiwang invoice issuance failed: {result.get('error', 'Unknown error')}",
            )
        return result.get('response', {})

    def query_invoice(self, query_data: dict):
        """Query issued invoices."""
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_query_invoice(self.company, query_data)
        if not result.get('success'):
            raise UserError(
                f"Baiwang invoice query failed: {result.get('error', 'Unknown error')}",
            )
        return result.get('response', {})

    def add_red_confirmation(self, red_form_data: dict):
        """
        Submit a red letter confirmation form (v7.0, flat body).

        Args:
            red_form_data: All red form fields (flat, top-level)

        Returns:
            Dictionary with response from Baiwang
        """
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_submit_red_form(self.company, red_form_data)
        if not result.get('success'):
            raise UserError(
                f"Baiwang red form submission failed: {result.get('error', 'Unknown error')}",
            )
        return result.get('response', {})

    def operate_red_confirmation(self, red_confirm_uuid: str, red_confirm_no: str, confirm_type: str):
        """
        Operate on a red confirmation form (confirm/deny/revoke).

        Args:
            red_confirm_uuid: Red confirmation UUID
            red_confirm_no: Red confirmation number
            confirm_type: '01'=confirm, '02'=deny, '03'=revoke

        Returns:
            Dictionary with response from Baiwang
        """
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_operate_red_form(
            self.company, red_confirm_uuid, red_confirm_no, confirm_type,
        )
        if not result.get('success'):
            raise UserError(
                f"Baiwang red form operation failed: {result.get('error', 'Unknown error')}",
            )
        return result.get('response', {})

    def query_red_form_list(self, filters: dict | None = None):
        """Query red confirmation form list (v7.0, flat body)."""
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_poll_red_form_list(self.company, filters)
        if not result.get('success'):
            raise UserError(
                f"Baiwang red form list query failed: {result.get('error', 'Unknown error')}",
            )
        return result.get('response', {})

    def query_red_form_detail(self, red_confirm_uuid: str):
        """Get red form detail (v6.0, flat body)."""
        self._ensure_proxy_user()
        result = self.proxy_user._l10n_cn_baiwang_query_red_form(self.company, red_confirm_uuid)
        if not result.get('success'):
            raise UserError(
                f"Baiwang red form detail query failed: {result.get('error', 'Unknown error')}",
            )
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
