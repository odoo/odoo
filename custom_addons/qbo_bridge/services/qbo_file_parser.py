"""QBOFileParser — converts QBO file exports into the same canonical dict
structure that QBOApiClient returns from the live API.

Supported formats
-----------------
* CSV  — QBO report exports (column headers vary by report type)
* XLSX — same reports in Excel format
* JSON — manual API export (already close to API shape, minor normalization)

The goal is to produce dicts that QBOSyncEngine can consume identically
whether data came from the live API or a file upload.
"""
import csv
import io
import json
import logging

_logger = logging.getLogger(__name__)

# ── Entity type → expected column alias maps (QBO report headers vary) ─────
# Keys are lowercase normalized column names; values are canonical field names.
_ACCOUNT_COLUMNS = {
    "name": "Name",
    "account name": "Name",
    "type": "AccountType",
    "account type": "AccountType",
    "detail type": "AccountSubType",
    "subtype": "AccountSubType",
    "balance": "CurrentBalance",
    "current balance": "CurrentBalance",
    "description": "Description",
    "active": "Active",
}

_CUSTOMER_COLUMNS = {
    "customer": "DisplayName",
    "name": "DisplayName",
    "display name": "DisplayName",
    "company": "CompanyName",
    "email": "PrimaryEmailAddr",
    "phone": "PrimaryPhone",
    "balance": "Balance",
    "active": "Active",
}

_VENDOR_COLUMNS = {
    "vendor": "DisplayName",
    "name": "DisplayName",
    "display name": "DisplayName",
    "company": "CompanyName",
    "email": "PrimaryEmailAddr",
    "phone": "PrimaryPhone",
    "balance": "Balance",
    "active": "Active",
}

_INVOICE_COLUMNS = {
    "invoice no": "DocNumber",
    "invoice #": "DocNumber",
    "num": "DocNumber",
    "customer": "CustomerRef",
    "date": "TxnDate",
    "due date": "DueDate",
    "amount": "TotalAmt",
    "total": "TotalAmt",
    "balance": "Balance",
    "status": "EmailStatus",
}

_PRODUCT_COLUMNS = {
    "product/service": "Name",
    "name": "Name",
    "type": "Type",
    "description": "Description",
    "price": "UnitPrice",
    "sales price": "UnitPrice",
    "cost": "PurchaseCost",
    "sku": "Sku",
    "active": "Active",
}

_COLUMN_MAPS = {
    "account": _ACCOUNT_COLUMNS,
    "partner": {**_CUSTOMER_COLUMNS, **_VENDOR_COLUMNS},
    "customer": _CUSTOMER_COLUMNS,
    "vendor": _VENDOR_COLUMNS,
    "invoice": _INVOICE_COLUMNS,
    "product": _PRODUCT_COLUMNS,
}


class QBOFileParseError(Exception):
    pass


class QBOFileParser:
    """Parse a QBO file export and return a list of normalized entity dicts."""

    def parse(self, file_content: bytes, file_type: str, entity_type: str) -> list[dict]:
        """Entry point.

        Parameters
        ----------
        file_content : bytes
            Raw file bytes.
        file_type : str
            One of ``csv``, ``xlsx``, ``json``.
        entity_type : str
            One of ``account``, ``partner``, ``invoice``, ``payment``,
            ``journal_entry``, ``product``.

        Returns
        -------
        list[dict]
            List of normalized dicts ready for QBOSyncEngine consumption.
        """
        ftype = file_type.lower().strip(".")
        if ftype == "csv":
            rows = self._parse_csv(file_content)
        elif ftype in ("xlsx", "xls"):
            rows = self._parse_xlsx(file_content)
        elif ftype == "json":
            return self._parse_json(file_content, entity_type)
        else:
            raise QBOFileParseError(f"Unsupported file type: {file_type}")

        return [self._normalize_row(row, entity_type) for row in rows if row]

    # ── Raw readers ───────────────────────────────────────────────────────────

    def _parse_csv(self, content: bytes) -> list[dict]:
        """Read CSV bytes into a list of dicts (headers as keys)."""
        text = content.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]

    def _parse_xlsx(self, content: bytes) -> list[dict]:
        """Read XLSX bytes using openpyxl into a list of dicts."""
        try:
            import openpyxl
        except ImportError as exc:
            raise QBOFileParseError(
                "openpyxl is required for XLSX import. Install it with: pip install openpyxl"
            ) from exc

        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []

        # First non-empty row is the header
        header_idx = 0
        for i, row in enumerate(rows):
            if any(cell for cell in row):
                header_idx = i
                break

        headers = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
        result = []
        for row in rows[header_idx + 1:]:
            if not any(cell for cell in row):
                continue
            result.append(
                {headers[j]: (str(cell).strip() if cell is not None else "") for j, cell in enumerate(row)}
            )
        return result

    def _parse_json(self, content: bytes, entity_type: str) -> list[dict]:
        """Parse JSON export. QBO JSON exports are already close to API shape."""
        try:
            data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise QBOFileParseError(f"Invalid JSON: {exc}") from exc

        # Handle both a raw list and the QueryResponse wrapper shape
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # QueryResponse wrapper
            qr = data.get("QueryResponse", {})
            for key in ("Account", "Customer", "Vendor", "Invoice", "Bill",
                        "Payment", "JournalEntry", "Item"):
                if key in qr:
                    return qr[key]
            # Flat dict with entity array at top level
            for key in data:
                if isinstance(data[key], list):
                    return data[key]
        return []

    # ── Normalizer ────────────────────────────────────────────────────────────

    def _normalize_row(self, row: dict, entity_type: str) -> dict:
        """Map arbitrary CSV/XLSX column headers to canonical QBO API field names."""
        col_map = _COLUMN_MAPS.get(entity_type, {})
        normalized = {}
        for raw_key, value in row.items():
            canonical = col_map.get(raw_key.strip().lower())
            if canonical:
                normalized[canonical] = value
            else:
                # Preserve unknown columns under their original name
                normalized[raw_key] = value

        # Coerce Active field to boolean
        if "Active" in normalized:
            normalized["Active"] = str(normalized["Active"]).strip().lower() not in (
                "false", "0", "no", "inactive", ""
            )

        # Mark as file-sourced so the sync engine skips the push-back check
        normalized["_source"] = "file"
        return normalized
