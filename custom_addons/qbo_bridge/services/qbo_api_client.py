"""QBOApiClient — thin wrapper around the QuickBooks Online REST v3 API.

Responsibilities
----------------
* Ensure a valid access token before every request (auto-refresh).
* Provide entity-level query methods used by QBOSyncEngine.
* Provide write methods (create / update) for push direction.
* Raise QBOApiError on HTTP or API-level errors with structured detail.
"""
import logging
from datetime import datetime

import requests
from odoo import fields

_logger = logging.getLogger(__name__)

# QBO query endpoint — all reads go through this
_QUERY_ENDPOINT = "query"

# Max results per page (QBO max is 1000)
PAGE_SIZE = 500


class QBOApiError(Exception):
    """Raised when the QBO API returns an error response."""

    def __init__(self, message, status_code=None, fault=None):
        super().__init__(message)
        self.status_code = status_code
        self.fault = fault


class QBOApiClient:
    """Wraps a single qbo.realm and exposes typed read/write methods.

    Usage
    -----
    ::

        client = QBOApiClient(realm_record)
        accounts = client.get_accounts(modified_since=last_sync)
    """

    def __init__(self, realm):
        self.realm = realm

    # =========================================================================
    # Low-level HTTP
    # =========================================================================

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.realm.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _ensure_token(self):
        """Refresh the access token if it is expired or within 60 s of expiry."""
        now = fields.Datetime.now()
        expiry = self.realm.token_expiry
        if not expiry or (expiry - now).total_seconds() < 60:
            self.realm._refresh_access_token()

    def get(self, endpoint, params=None):
        """HTTP GET against the realm's base URL."""
        self._ensure_token()
        url = f"{self.realm.api_base_url}/{endpoint}"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=20)
        return self._handle_response(resp)

    def post(self, endpoint, payload):
        """HTTP POST (create)."""
        self._ensure_token()
        url = f"{self.realm.api_base_url}/{endpoint}"
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=20)
        return self._handle_response(resp)

    def _handle_response(self, resp):
        if resp.status_code == 401:
            # Token may have been revoked — clear and raise
            self.realm.sudo().write({"state": "error", "last_error": "401 Unauthorized"})
            raise QBOApiError("QBO returned 401 — re-authorise the connection.", 401)
        try:
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            fault = None
            try:
                fault = resp.json()
            except Exception:
                pass
            raise QBOApiError(str(exc), resp.status_code, fault) from exc

    # =========================================================================
    # Generic paginated query
    # =========================================================================

    def query(self, entity, where=None, modified_since=None, select="*"):
        """Execute a QBO SQL-like query with automatic pagination.

        Parameters
        ----------
        entity : str
            QBO entity name, e.g. ``Account``, ``Customer``, ``Invoice``.
        where : str, optional
            Additional WHERE clause fragment, e.g. ``"Active = true"``.
        modified_since : datetime, optional
            ISO-8601 string or datetime; adds ``MetaData.LastUpdatedTime >= ...``.
        select : str
            Columns to select (default ``*``).

        Yields
        ------
        dict
            Each entity record from the API.
        """
        conditions = []
        if where:
            conditions.append(where)
        if modified_since:
            if isinstance(modified_since, datetime):
                ts = modified_since.strftime("%Y-%m-%dT%H:%M:%S-00:00")
            else:
                ts = modified_since
            conditions.append(f"MetaData.LastUpdatedTime >= '{ts}'")

        where_clause = " AND ".join(conditions)
        start = 1
        while True:
            sql = f"SELECT {select} FROM {entity}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            sql += f" STARTPOSITION {start} MAXRESULTS {PAGE_SIZE}"

            data = self.get(_QUERY_ENDPOINT, params={"query": sql})
            resp_body = data.get("QueryResponse", {})
            items = resp_body.get(entity, [])
            yield from items
            if len(items) < PAGE_SIZE:
                break
            start += PAGE_SIZE

    # =========================================================================
    # Chart of Accounts
    # =========================================================================

    def get_accounts(self, modified_since=None):
        """Yield all QBO Account records, optionally filtered by modified date."""
        return list(self.query("Account", modified_since=modified_since))

    def create_account(self, payload):
        """POST a new Account to QBO. Returns the created Account dict."""
        return self.post("account", payload).get("Account", {})

    def update_account(self, payload):
        """POST a sparse Account update (must include Id + SyncToken)."""
        return self.post("account?operation=update", payload).get("Account", {})

    # =========================================================================
    # Customers & Vendors
    # =========================================================================

    def get_customers(self, modified_since=None):
        return list(self.query("Customer", modified_since=modified_since))

    def get_vendors(self, modified_since=None):
        return list(self.query("Vendor", modified_since=modified_since))

    def create_customer(self, payload):
        return self.post("customer", payload).get("Customer", {})

    def update_customer(self, payload):
        return self.post("customer?operation=update", payload).get("Customer", {})

    def create_vendor(self, payload):
        return self.post("vendor", payload).get("Vendor", {})

    def update_vendor(self, payload):
        return self.post("vendor?operation=update", payload).get("Vendor", {})

    # =========================================================================
    # Invoices & Bills
    # =========================================================================

    def get_invoices(self, modified_since=None):
        return list(self.query("Invoice", modified_since=modified_since))

    def get_bills(self, modified_since=None):
        return list(self.query("Bill", modified_since=modified_since))

    def create_invoice(self, payload):
        return self.post("invoice", payload).get("Invoice", {})

    def update_invoice(self, payload):
        return self.post("invoice?operation=update", payload).get("Invoice", {})

    def create_bill(self, payload):
        return self.post("bill", payload).get("Bill", {})

    def update_bill(self, payload):
        return self.post("bill?operation=update", payload).get("Bill", {})

    # =========================================================================
    # Payments & Transactions
    # =========================================================================

    def get_payments(self, modified_since=None):
        return list(self.query("Payment", modified_since=modified_since))

    def get_bill_payments(self, modified_since=None):
        return list(self.query("BillPayment", modified_since=modified_since))

    def create_payment(self, payload):
        return self.post("payment", payload).get("Payment", {})

    # =========================================================================
    # Journal Entries
    # =========================================================================

    def get_journal_entries(self, modified_since=None):
        return list(self.query("JournalEntry", modified_since=modified_since))

    def create_journal_entry(self, payload):
        return self.post("journalentry", payload).get("JournalEntry", {})

    def update_journal_entry(self, payload):
        return self.post("journalentry?operation=update", payload).get("JournalEntry", {})

    # =========================================================================
    # Products / Items
    # =========================================================================

    def get_items(self, modified_since=None):
        return list(self.query("Item", modified_since=modified_since))

    def create_item(self, payload):
        return self.post("item", payload).get("Item", {})

    def update_item(self, payload):
        return self.post("item?operation=update", payload).get("Item", {})

    # =========================================================================
    # Company info (used for connection test)
    # =========================================================================

    def get_company_info(self):
        return self.get(f"companyinfo/{self.realm.realm_id}")
