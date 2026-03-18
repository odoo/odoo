"""QBOSyncEngine — orchestrates bidirectional sync between QBO and Odoo.

Conflict strategy
-----------------
When both sides have changed since ``last_sync``:
  1. A ``qbo.conflict`` record is created with JSON snapshots of both versions.
  2. A ``qbo.sync.log`` record is written with ``status='conflict'``.
  3. The record is NOT written to either side until the user resolves it.

Entity field mappings (QBO → Odoo) are implemented as ``_map_*`` methods.
Push mappings (Odoo → QBO) are in the corresponding ``_odoo_to_qbo_*`` methods.

TODO for each entity
--------------------
Each ``_sync_*`` method has a ``# TODO`` marking where the Odoo model write /
update logic needs to be completed with your specific chart of account
structure, journal types, and partner categories.
"""
import json
import logging
import re
import time
from contextlib import suppress
from datetime import datetime, timezone

from odoo import fields

from ..models.qbo_sync_log import QboSyncLog
from .qbo_api_client import QBOApiClient, QBOApiError

_logger = logging.getLogger(__name__)

# Fields used to detect meaningful changes (by entity type)
_CONFLICT_FIELDS = {
    "account": ["Name", "AccountType", "AccountSubType", "Active", "Description"],
    "partner": ["DisplayName", "CompanyName", "PrimaryEmailAddr", "Active", "Balance"],
    "invoice": ["TotalAmt", "Balance", "DueDate", "EmailStatus"],
    "payment": ["TotalAmt", "TxnDate"],
    "journal_entry": ["TotalAmt", "TxnDate", "Adjustment"],
    "product": ["Name", "UnitPrice", "PurchaseCost", "Type", "Active"],
}

# Odoo model names per entity type
_ODOO_MODELS = {
    "account": "account.account",
    "partner": "res.partner",
    "invoice": "account.move",
    "payment": "account.payment",
    "journal_entry": "account.move",
    "product": "product.template",
}


class QBOSyncEngine:
    """Stateful sync session for one qbo.company.mapping record."""

    def __init__(self, env, mapping):
        self.env = env
        self.mapping = mapping
        self.client = QBOApiClient(mapping.realm_id)
        self._stats = {
            "created": 0, "updated": 0, "skipped": 0, "conflicts": 0, "errors": 0,
        }

    # =========================================================================
    # Public entry points
    # =========================================================================

    def sync_all(self):
        """Run all enabled entity syncs for this mapping."""
        m = self.mapping
        _logger.info("QBO sync start: %s", m.display_name)
        if m.sync_accounts:
            self._safe_sync("account", self._sync_accounts)
        if m.sync_partners:
            self._safe_sync("partner", self._sync_partners)
        if m.sync_products:
            self._safe_sync("product", self._sync_products)
        if m.sync_invoices:
            self._safe_sync("invoice", self._sync_invoices)
        if m.sync_payments:
            self._safe_sync("payment", self._sync_payments)
        if m.sync_journal_entries:
            self._safe_sync("journal_entry", self._sync_journal_entries)
        _logger.info("QBO sync complete: %s | %s", m.display_name, self._stats)

    def sync_from_file(self, records: list[dict], entity_type: str):
        """Import pre-parsed file records for one entity type."""
        dispatcher = {
            "account": self._upsert_accounts,
            "partner": self._upsert_partners,
            "invoice": self._upsert_invoices,
            "payment": self._upsert_payments,
            "product": self._upsert_products,
            "journal_entry": self._upsert_journal_entries,
        }
        fn = dispatcher.get(entity_type)
        if not fn:
            raise ValueError(f"Unknown entity type: {entity_type}")
        fn(records, direction="pull")

    # =========================================================================
    # Per-entity sync orchestrators
    # =========================================================================

    def _sync_accounts(self):
        last = self.mapping.get_last_sync_for("account")
        qbo_records = self.client.get_accounts(modified_since=last)
        self._upsert_accounts(qbo_records, direction="pull")
        self._push_accounts(since=last)
        self.mapping.set_last_sync_for("account")

    def _sync_partners(self):
        last = self.mapping.get_last_sync_for("partner")
        customers = self.client.get_customers(modified_since=last)
        vendors = self.client.get_vendors(modified_since=last)
        all_partners = [{"_qbo_type": "customer", **r} for r in customers] + \
                       [{"_qbo_type": "vendor", **r} for r in vendors]
        self._upsert_partners(all_partners, direction="pull")
        self._push_partners(since=last)
        self.mapping.set_last_sync_for("partner")

    def _sync_invoices(self):
        last = self.mapping.get_last_sync_for("invoice")
        invoices = self.client.get_invoices(modified_since=last)
        bills = self.client.get_bills(modified_since=last)
        combined = [{"_qbo_type": "invoice", **r} for r in invoices] + \
                   [{"_qbo_type": "bill", **r} for r in bills]
        self._upsert_invoices(combined, direction="pull")
        self._push_invoices(since=last)
        self.mapping.set_last_sync_for("invoice")

    def _sync_payments(self):
        last = self.mapping.get_last_sync_for("payment")
        payments = self.client.get_payments(modified_since=last)
        bill_payments = self.client.get_bill_payments(modified_since=last)
        combined = [{"_qbo_type": "payment", **r} for r in payments] + \
                   [{"_qbo_type": "bill_payment", **r} for r in bill_payments]
        self._upsert_payments(combined, direction="pull")
        self.mapping.set_last_sync_for("payment")

    def _sync_journal_entries(self):
        last = self.mapping.get_last_sync_for("journal_entry")
        entries = self.client.get_journal_entries(modified_since=last)
        self._upsert_journal_entries(entries, direction="pull")
        self.mapping.set_last_sync_for("journal_entry")

    def _sync_products(self):
        last = self.mapping.get_last_sync_for("product")
        items = self.client.get_items(modified_since=last)
        self._upsert_products(items, direction="pull")
        self._push_products(since=last)
        self.mapping.set_last_sync_for("product")

    # =========================================================================
    # Upsert helpers (QBO → Odoo, pull direction)
    # =========================================================================

    def _upsert_accounts(self, qbo_records, direction="pull"):
        """Create or update Odoo account.account records from QBO Account data."""
        AccountAccount = self.env["account.account"].with_company(self.mapping.company_id)
        for rec in qbo_records:
            t0 = time.monotonic()
            qbo_id = rec.get("Id")
            try:
                odoo_vals = self._map_account_to_odoo(rec)
                existing = AccountAccount.search(
                    [
                        ("qbo_id", "=", qbo_id),
                        ("company_ids", "=", self.mapping.company_id.id),
                    ],
                    limit=1,
                ) if qbo_id else None
                if not existing and odoo_vals.get("code"):
                    existing = AccountAccount.search(
                        [
                            ("company_ids", "=", self.mapping.company_id.id),
                            ("code", "=", odoo_vals["code"]),
                            ("qbo_id", "=", False),
                        ],
                        limit=1,
                    )

                if existing:
                    conflict = self._detect_conflict(existing, rec, "account")
                    if conflict:
                        self._create_conflict(existing, rec, "account")
                        continue
                    existing.write(odoo_vals)
                    self._log("account", direction, "success", qbo_id, existing, t0)
                else:
                    new_rec = AccountAccount.create(odoo_vals)
                    self._log("account", direction, "success", qbo_id, new_rec, t0)
            except Exception as exc:
                _logger.exception("Account upsert failed for QBO ID %s", qbo_id)
                self._log("account", direction, "error", qbo_id, None, t0, str(exc))

    def _upsert_partners(self, qbo_records, direction="pull"):
        """Create or update res.partner records from QBO Customer/Vendor data."""
        Partner = self.env["res.partner"].with_company(self.mapping.company_id)
        for rec in qbo_records:
            t0 = time.monotonic()
            qbo_id = rec.get("Id")
            try:
                odoo_vals = self._map_partner_to_odoo(rec)
                existing = Partner.search([("qbo_id", "=", qbo_id)], limit=1) if qbo_id else None
                if existing:
                    if self._detect_conflict(existing, rec, "partner"):
                        self._create_conflict(existing, rec, "partner")
                        continue
                    existing.write(odoo_vals)
                    self._log("partner", direction, "success", qbo_id, existing, t0)
                else:
                    new_rec = Partner.create(odoo_vals)
                    self._log("partner", direction, "success", qbo_id, new_rec, t0)
            except Exception as exc:
                _logger.exception("Partner upsert failed for QBO ID %s", qbo_id)
                self._log("partner", direction, "error", qbo_id, None, t0, str(exc))

    def _upsert_invoices(self, qbo_records, direction="pull"):
        """Create or update account.move records from QBO Invoice/Bill data."""
        Move = self.env["account.move"].with_company(self.mapping.company_id)
        for rec in qbo_records:
            t0 = time.monotonic()
            qbo_id = rec.get("Id")
            try:
                odoo_vals = self._map_invoice_to_odoo(rec)
                existing = Move.search([("qbo_id", "=", qbo_id)], limit=1) if qbo_id else None
                if existing:
                    if self._detect_conflict(existing, rec, "invoice"):
                        self._create_conflict(existing, rec, "invoice")
                        continue
                    if existing.state == "draft":
                        existing.write(odoo_vals)
                    # Posted invoices: create a correction move or log skip
                    self._log("invoice", direction, "success", qbo_id, existing, t0)
                else:
                    new_rec = Move.create(odoo_vals)
                    self._log("invoice", direction, "success", qbo_id, new_rec, t0)
            except Exception as exc:
                _logger.exception("Invoice upsert failed for QBO ID %s", qbo_id)
                self._log("invoice", direction, "error", qbo_id, None, t0, str(exc))

    def _upsert_payments(self, qbo_records, direction="pull"):
        # TODO: implement account.payment upsert from QBO Payment/BillPayment
        for rec in qbo_records:
            t0 = time.monotonic()
            qbo_id = rec.get("Id")
            _logger.debug("Payment upsert stub: QBO ID %s", qbo_id)
            self._log("payment", direction, "skipped", qbo_id, None, t0, "Not yet implemented")

    def _upsert_journal_entries(self, qbo_records, direction="pull"):
        # TODO: implement account.move (journal entry type) upsert from QBO JournalEntry
        for rec in qbo_records:
            t0 = time.monotonic()
            qbo_id = rec.get("Id")
            _logger.debug("JE upsert stub: QBO ID %s", qbo_id)
            self._log("journal_entry", direction, "skipped", qbo_id, None, t0, "Not yet implemented")

    def _upsert_products(self, qbo_records, direction="pull"):
        """Create or update product.template records from QBO Item data."""
        Product = self.env["product.template"].with_company(self.mapping.company_id)
        for rec in qbo_records:
            t0 = time.monotonic()
            qbo_id = rec.get("Id")
            try:
                odoo_vals = self._map_product_to_odoo(rec)
                existing = Product.search([("qbo_id", "=", qbo_id)], limit=1) if qbo_id else None
                if existing:
                    if self._detect_conflict(existing, rec, "product"):
                        self._create_conflict(existing, rec, "product")
                        continue
                    existing.write(odoo_vals)
                    self._log("product", direction, "success", qbo_id, existing, t0)
                else:
                    new_rec = Product.create(odoo_vals)
                    self._log("product", direction, "success", qbo_id, new_rec, t0)
            except Exception as exc:
                _logger.exception("Product upsert failed for QBO ID %s", qbo_id)
                self._log("product", direction, "error", qbo_id, None, t0, str(exc))

    # =========================================================================
    # Push helpers (Odoo → QBO)
    # =========================================================================

    def _push_accounts(self, since=None):
        """Push Odoo accounts modified after ``since`` that have no qbo_id yet,
        or whose write_date > last QBO update (conflict already resolved)."""
        domain = [("company_ids", "=", self.mapping.company_id.id), ("qbo_id", "=", False)]
        if since:
            domain.append(("write_date", ">=", since))
        accounts = self.env["account.account"].search(domain)
        for acc in accounts:
            self.push_account_record(acc)

    def _push_partners(self, since=None):
        # TODO: push new/updated Odoo partners without a qbo_id
        pass

    def _push_invoices(self, since=None):
        # TODO: push new/updated Odoo invoices without a qbo_id
        pass

    def _push_products(self, since=None):
        # TODO: push new/updated Odoo products without a qbo_id
        pass

    # =========================================================================
    # Field mapping: QBO → Odoo
    # =========================================================================

    def _map_account_to_odoo(self, rec):
        """Map a QBO Account dict to account.account write values.

        TODO: refine account_type mapping to match your Kodoo CoA structure.
        """
        bridge_rule = self._match_account_bridge_rule(rec)
        qbo_type = rec.get("AccountType", "")
        account_type = _QBO_ACCOUNT_TYPE_MAP.get(qbo_type, "asset_current")
        code = (
            bridge_rule.canonical_code
            if bridge_rule
            else self._normalize_account_code(rec.get("AcctNum"), rec.get("Id"))
        )
        vals = {
            "name": bridge_rule.canonical_name if bridge_rule else rec.get("Name", ""),
            "code": code,
            "account_type": bridge_rule.canonical_account_type if bridge_rule else account_type,
            "note": rec.get("Description", ""),
            "active": rec.get("Active", True),
            "qbo_id": rec.get("Id"),
            "qbo_sync_token": rec.get("SyncToken"),
            "qbo_bridge_rule_id": bridge_rule.id if bridge_rule else False,
            "qbo_source_name": rec.get("Name", ""),
            "qbo_source_account_number": rec.get("AcctNum", ""),
            "qbo_source_account_type": qbo_type,
            "qbo_source_account_subtype": rec.get("AccountSubType", ""),
            "company_ids": [(4, self.mapping.company_id.id)],
        }
        if (
            bridge_rule
            and "standard_account_id" in bridge_rule._fields
            and bridge_rule.standard_account_id
            and "qbo_standard_account_id" in self.env["account.account"]._fields
        ):
            vals["qbo_standard_account_id"] = bridge_rule.standard_account_id.id
        return vals

    def _map_partner_to_odoo(self, rec):
        """Map QBO Customer or Vendor to res.partner values."""
        qbo_type = rec.get("_qbo_type", "customer")
        email_obj = rec.get("PrimaryEmailAddr", {})
        phone_obj = rec.get("PrimaryPhone", {})
        addr = rec.get("BillAddr", {})
        return {
            "name": rec.get("DisplayName") or rec.get("CompanyName", ""),
            "company_name": rec.get("CompanyName", ""),
            "email": email_obj.get("Address", "") if isinstance(email_obj, dict) else email_obj,
            "phone": phone_obj.get("FreeFormNumber", "") if isinstance(phone_obj, dict) else phone_obj,
            "street": addr.get("Line1", "") if isinstance(addr, dict) else "",
            "city": addr.get("City", "") if isinstance(addr, dict) else "",
            "zip": addr.get("PostalCode", "") if isinstance(addr, dict) else "",
            "customer_rank": 1 if qbo_type == "customer" else 0,
            "supplier_rank": 1 if qbo_type == "vendor" else 0,
            "active": rec.get("Active", True),
            "qbo_id": rec.get("Id"),
            "qbo_sync_token": rec.get("SyncToken"),
            "company_id": self.mapping.company_id.id,
        }

    def _map_invoice_to_odoo(self, rec):
        """Map QBO Invoice or Bill to account.move values.

        TODO: resolve CustomerRef/VendorRef to res.partner IDs.
        TODO: map line items to account.move.line.
        """
        qbo_type = rec.get("_qbo_type", "invoice")
        move_type = "out_invoice" if qbo_type == "invoice" else "in_invoice"
        return {
            "move_type": move_type,
            "name": rec.get("DocNumber", "/"),
            "invoice_date": rec.get("TxnDate"),
            "invoice_date_due": rec.get("DueDate"),
            "qbo_id": rec.get("Id"),
            "qbo_sync_token": rec.get("SyncToken"),
            "company_id": self.mapping.company_id.id,
            # TODO: partner_id = self._resolve_partner(rec)
            # TODO: invoice_line_ids = self._map_invoice_lines(rec)
        }

    def _map_product_to_odoo(self, rec):
        """Map a QBO Item to product.template values."""
        return {
            "name": rec.get("Name", ""),
            "description_sale": rec.get("Description", ""),
            "list_price": float(rec.get("UnitPrice", 0.0)),
            "standard_price": float(rec.get("PurchaseCost", 0.0)),
            "active": rec.get("Active", True),
            "default_code": rec.get("Sku", ""),
            "qbo_id": rec.get("Id"),
            "qbo_sync_token": rec.get("SyncToken"),
        }

    # =========================================================================
    # Field mapping: Odoo → QBO
    # =========================================================================

    def _odoo_account_to_qbo(self, acc):
        """Map an Odoo account.account to a QBO Account create payload."""
        qbo_type = _ODOO_ACCOUNT_TYPE_MAP.get(acc.account_type, "OtherAsset")
        return {
            "Name": acc.name,
            "AccountType": qbo_type,
            "AcctNum": acc.code or "",
            "Description": acc.note or "",
            "Active": acc.active,
        }

    def _match_account_bridge_rule(self, rec):
        return self.env["qbo.account.bridge.rule"].match_qbo_record(rec)

    def push_account_record(self, account):
        t0 = time.monotonic()
        try:
            payload = self._odoo_account_to_qbo(account)
            if account.qbo_id:
                payload.update(
                    {
                        "Id": account.qbo_id,
                        "SyncToken": account.qbo_sync_token or "0",
                        "sparse": True,
                    },
                )
                result = self.client.update_account(payload)
            else:
                result = self.client.create_account(payload)

            write_vals = {
                "qbo_id": result.get("Id"),
                "qbo_sync_token": result.get("SyncToken"),
                "qbo_last_sync": fields.Datetime.now(),
            }
            if "qbo_realm_id" in account._fields:
                write_vals["qbo_realm_id"] = self.mapping.realm_id.id
            if (
                "qbo_standard_account_id" in account._fields
                and "standard_account_id" in self.env["qbo.account.bridge.rule"]._fields
                and account.qbo_bridge_rule_id.standard_account_id
            ):
                write_vals["qbo_standard_account_id"] = (
                    account.qbo_bridge_rule_id.standard_account_id.id
                )

            account.sudo().write(write_vals)
            self._log("account", "push", "success", result.get("Id"), account, t0)
            return result
        except Exception as exc:
            _logger.exception("Push account %s failed", account.display_name)
            self._log(
                "account",
                "push",
                "error",
                account.qbo_id,
                account,
                t0,
                str(exc),
            )
            raise

    # =========================================================================
    # Conflict detection
    # =========================================================================

    def _detect_conflict(self, odoo_record, qbo_record, entity_type):
        """Return True if both sides have changed since last sync.

        Logic: odoo_record.write_date > last_sync AND qbo_record.MetaData.LastUpdatedTime > last_sync
        """
        last_sync = self.mapping.get_last_sync_for(entity_type)
        if not last_sync:
            return False  # First sync — no conflict possible

        # QBO last update
        meta = qbo_record.get("MetaData", {})
        qbo_updated_str = meta.get("LastUpdatedTime", "")
        if not qbo_updated_str:
            return False
        qbo_updated = self._parse_qbo_datetime(qbo_updated_str)
        if not qbo_updated:
            return False

        odoo_write = getattr(odoo_record, "write_date", None)
        if not odoo_write:
            return False

        # Both sides changed after last sync → conflict
        return odoo_write > last_sync and qbo_updated > last_sync

    def _create_conflict(self, odoo_record, qbo_record, entity_type):
        """Create a qbo.conflict record for manual review."""
        meta = qbo_record.get("MetaData", {})
        qbo_last_updated = self._parse_qbo_datetime(meta.get("LastUpdatedTime"))

        # Build a lightweight Odoo snapshot (only conflict-relevant fields)
        odoo_snapshot = {}
        for fname in _CONFLICT_FIELDS.get(entity_type, []):
            with suppress(Exception):
                odoo_snapshot[fname] = str(getattr(odoo_record, fname.lower(), ""))

        self.env["qbo.conflict"].sudo().create({
            "mapping_id": self.mapping.id,
            "entity_type": entity_type,
            "qbo_id": qbo_record.get("Id"),
            "odoo_model": _ODOO_MODELS.get(entity_type),
            "odoo_record_id": odoo_record.id,
            "odoo_data": json.dumps(odoo_snapshot),
            "qbo_data": json.dumps({k: qbo_record.get(k) for k in _CONFLICT_FIELDS.get(entity_type, [])}),
            "odoo_write_date": getattr(odoo_record, "write_date", False),
            "qbo_last_updated": fields.Datetime.to_string(qbo_last_updated) if qbo_last_updated else False,
        })
        self._stats["conflicts"] += 1
        QboSyncLog.log(
            self.env, self.mapping, entity_type, "conflict", "conflict",
            qbo_id=qbo_record.get("Id"),
            odoo_model=_ODOO_MODELS.get(entity_type),
            odoo_record_id=odoo_record.id,
            message="Both sides modified since last sync — flagged for review",
        )

    # =========================================================================
    # Utilities
    # =========================================================================

    def _safe_sync(self, entity_type, fn):
        try:
            fn()
        except QBOApiError as exc:
            _logger.error("QBO API error syncing %s: %s", entity_type, exc)
            self.mapping.realm_id._set_error(str(exc))
        except Exception:
            _logger.exception("Unexpected error syncing %s", entity_type)

    def _log(self, entity_type, direction, status, qbo_id, odoo_record, t0, message=None):
        duration_ms = int((time.monotonic() - t0) * 1000)
        QboSyncLog.log(
            self.env, self.mapping, entity_type, direction, status,
            qbo_id=qbo_id,
            odoo_model=_ODOO_MODELS.get(entity_type) if odoo_record else None,
            odoo_record_id=odoo_record.id if odoo_record else None,
            message=message,
            duration_ms=duration_ms,
        )
        self._stats[status if status in self._stats else "skipped"] += 1

    def _normalize_account_code(self, raw_code, qbo_id):
        for candidate in (raw_code, qbo_id):
            if not candidate:
                continue
            sanitized = re.sub(r"[^A-Za-z0-9.]+", "", str(candidate)).strip(".")
            if sanitized:
                return sanitized[:64]
        return False

    def _parse_qbo_datetime(self, value):
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed


# ── Account type translation tables ──────────────────────────────────────────

_QBO_ACCOUNT_TYPE_MAP = {
    "Bank": "asset_cash",
    "Accounts Receivable": "asset_receivable",
    "Other Current Asset": "asset_current",
    "Fixed Asset": "asset_fixed",
    "Other Asset": "asset_non_current",
    "Accounts Payable": "liability_payable",
    "Credit Card": "liability_credit_card",
    "Other Current Liability": "liability_current",
    "Long Term Liability": "liability_non_current",
    "Equity": "equity",
    "Income": "income",
    "Cost of Goods Sold": "expense_direct_cost",
    "Expense": "expense",
    "Other Income": "income_other",
    "Other Expense": "expense_other",
}

_ODOO_ACCOUNT_TYPE_MAP = {v: k for k, v in _QBO_ACCOUNT_TYPE_MAP.items()}
