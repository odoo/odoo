# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Baiwang EDI Client for Odoo (Thin Proxy Wrapper)

This module provides convenience methods that route all business calls through
the IAP proxy server. The proxy handles Baiwang credentials, OAuth tokens,
request signing, and API version management.

For development/testing, this can be swapped with a direct client that
talks to Baiwang without the proxy layer (see _legacy_direct_call comments).
"""

from odoo.exceptions import UserError

from odoo.addons.l10n_cn_edi_baiwang.exceptions import get_baiwang_error_message


class BaiwangClient:
    """
    Baiwang Open API client for e-Fapiao integration (Thin proxy wrapper).
    """

    def __init__(self, company):
        self.company = company
        self.proxy_user = company.l10n_cn_baiwang_proxy_user_id

    def _ensure_proxy_user(self):
        if not self.proxy_user:
            msg = self.company.env._(
                "Baiwang proxy user is not registered for this company. "
                "Please register it in Settings → Accounting → China Electronic Invoicing.",
            )
            raise UserError(msg)

    def ensure_connection(self):
        self._ensure_proxy_user()
        return True

    def _map_proxy_error(self, error):
        fallback = self.company.env._('Unexpected Baiwang proxy error.')
        if isinstance(error, str):
            return error or fallback
        if not isinstance(error, dict):
            return fallback

        reference = error.get('reference')
        data = error.get('data')
        if reference in {'provider_error', 'baiwang_api_error', 'baiwang_oauth_failed'}:
            return get_baiwang_error_message(self.company.env, reference, data)

        reference_mapping = {
            'invalid_payload': self.company.env._('The Baiwang request payload is invalid.'),
            'proxy_contact_failed': self.company.env._('Failed to contact the Baiwang proxy service. Please try again later.'),
        }
        if reference in reference_mapping:
            return reference_mapping[reference]

        if reference:
            return self.company.env._('Unexpected Baiwang proxy error (%s).') % reference
        return fallback

    def _call_proxy(self, method, *args, error_prefix="", allow_failed_with_response=False):
        self._ensure_proxy_user()
        result = method(self.company, *args)
        if not result.get('success') and not (allow_failed_with_response and 'response' in result):
            err_details = self._map_proxy_error(result.get('error'))
            # Safely format with %s if present, otherwise append
            msg = error_prefix % err_details if '%s' in error_prefix else f"{error_prefix}: {err_details}"
            raise UserError(msg)
        return result.get('response', {})

    def issue_invoice(self, invoice_data: dict):
        return self._call_proxy(
            self.proxy_user._l10n_cn_baiwang_issue_invoice,
            invoice_data,
            error_prefix=self.company.env._("Baiwang proxy error: %s"),
            allow_failed_with_response=True,
        )

    def query_invoice(self, query_data: dict):
        return self._call_proxy(
            self.proxy_user._l10n_cn_baiwang_query_invoice,
            query_data,
            error_prefix=self.company.env._("Baiwang invoice query failed: %s"),
        )

    def add_red_confirmation(self, red_form_data: dict):
        return self._call_proxy(
            self.proxy_user._l10n_cn_baiwang_submit_red_form,
            red_form_data,
            error_prefix=self.company.env._("Baiwang red form submission failed: %s"),
            allow_failed_with_response=True,
        )

    def operate_red_confirmation(self, red_confirm_uuid: str, red_confirm_no: str, confirm_type: str):
        return self._call_proxy(
            self.proxy_user._l10n_cn_baiwang_operate_red_form,
            red_confirm_uuid,
            red_confirm_no,
            confirm_type,
            error_prefix=self.company.env._("Baiwang red form operation failed: %s"),
        )

    def query_red_form_list(self, filters: dict | None = None):
        return self._call_proxy(
            self.proxy_user._l10n_cn_baiwang_poll_red_form_list,
            filters or {},
            error_prefix=self.company.env._("Baiwang red form list query failed: %s"),
        )

    def query_red_form_detail(self, red_confirm_uuid: str):
        return self._call_proxy(
            self.proxy_user._l10n_cn_baiwang_query_red_form,
            red_confirm_uuid,
            error_prefix=self.company.env._("Baiwang red form detail query failed: %s"),
        )
