# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Parse a received ETDA 3-2560 (ขมธอ.3-2560) e-Tax Invoice / e-Receipt.

This is the inbound counterpart of :mod:`xml_builder`: it reads the XML a
supplier issued and turns it into a plain dictionary the import wizard can
expand into a Vendor Bill.

The six document families ship one namespace each, so every lookup is done by
*local name* which keeps a single reader for all of them.  A trailing XAdES
``ds:Signature`` is stripped before the XSD check because the signature is an
optional extension the ETDA business schema does not declare.
"""

import datetime
import re

from lxml import etree

from . import namespaces, validator

_ROOT_SUFFIX = "_CrossIndustryInvoice"
_SIGNATURE_LOCAL = "Signature"

_DATETIME_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?"
)


class ParseError(Exception):
    """Raised when the file cannot be read as an ETDA e-Tax document."""


# ----------------------------------------------------------------------
# Low level helpers
# ----------------------------------------------------------------------
def _local(tag):
    """Return the local name of a qualified tag (``{ns}Name`` -> ``Name``)."""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _find(node, name):
    if node is None:
        return None
    for child in node:
        if _local(child.tag) == name:
            return child
    return None


def _findall(node, name):
    if node is None:
        return []
    return [child for child in node if _local(child.tag) == name]


def _text(node, name, default=None):
    found = _find(node, name)
    if found is None:
        return default
    return (found.text or "").strip() or default


def _amount(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalise_tax_id(value):
    """Return the 13 significant digits of a Thai tax identifier.

    A juristic person is reported with 13 digits plus a 5 digit branch code
    (18 digits total), so only the leading 13 digits are kept for matching.
    """
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:13]


def parse_datetime(value):
    """Return a :class:`datetime.datetime` from an ETDA ISO date/datetime."""
    if not value:
        return None
    match = _DATETIME_RE.search(str(value))
    if not match:
        return None
    year, month, day, hour, minute, second = match.groups()
    try:
        return datetime.datetime(
            int(year), int(month), int(day),
            int(hour or 0), int(minute or 0), int(second or 0),
        )
    except ValueError:
        return None


# ----------------------------------------------------------------------
# Document reader
# ----------------------------------------------------------------------
def load(xml_bytes):
    """Return the root :class:`lxml.etree._Element` of ``xml_bytes``."""
    if isinstance(xml_bytes, str):
        xml_bytes = xml_bytes.encode("utf-8")
    try:
        return etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as error:
        raise ParseError("อ่านไฟล์ XML ไม่ได้: %s" % error) from error


def document_type_of(root):
    """Return the :data:`namespaces.DOCUMENT_TYPES` key of ``root``."""
    local = _local(root.tag)
    if not local.endswith(_ROOT_SUFFIX):
        raise ParseError(
            "ไฟล์ XML ไม่ใช่เอกสาร e-Tax Invoice ตามมาตรฐาน ขมธอ.3-2560 "
            "(root element: %s)" % (local or root.tag)
        )
    class_name = local[: -len(_ROOT_SUFFIX)]
    for key, spec in namespaces.DOCUMENT_TYPES.items():
        if spec["class"] == class_name:
            return key
    raise ParseError("ไม่รู้จักประเภทเอกสาร e-Tax: %s" % class_name)


def _parse_address(node):
    if node is None:
        return {}
    return {
        "street": _text(node, "LineOne") or _text(node, "StreetName"),
        "street2": _text(node, "BuildingName"),
        "zip": _text(node, "PostcodeCode"),
        "country_code": _text(node, "CountryID"),
    }


def _parse_contact(node):
    contact = _find(node, "DefinedTradeContact")
    if contact is None:
        return {}
    email = None
    phone = None
    for child in contact:
        local = _local(child.tag)
        if "Email" in local:
            email = _text(child, "URIID") or _text(child, "CompleteNumber")
        elif "Telephone" in local:
            phone = _text(child, "CompleteNumber")
    return {"email": email, "phone": phone}


def _parse_party(node):
    """Return the name, tax registration and address of a trade party."""
    if node is None:
        return {}
    party = {
        "name": _text(node, "Name"),
        "code": _text(node, "ID"),
        "tax_id": None,
        "scheme_id": None,
    }
    registration = _find(node, "SpecifiedTaxRegistration")
    if registration is not None:
        id_node = _find(registration, "ID")
        if id_node is not None:
            party["tax_id"] = (id_node.text or "").strip() or None
            party["scheme_id"] = id_node.get("schemeID")
    party.update(_parse_contact(node))
    party["address"] = _parse_address(_find(node, "PostalTradeAddress"))
    return party


def _parse_tax(node):
    return {
        "type_code": _text(node, "TypeCode", "VAT"),
        "rate": _amount(_text(node, "CalculatedRate")),
        "base": _amount(_text(node, "BasisAmount")),
        "amount": _amount(_text(node, "CalculatedAmount")),
    }


def _parse_line(node, index):
    product = _find(node, "SpecifiedTradeProduct")
    agreement = _find(node, "SpecifiedLineTradeAgreement")
    price = _find(agreement, "GrossPriceProductTradePrice") if agreement is not None else None
    delivery = _find(node, "SpecifiedLineTradeDelivery")
    quantity_node = _find(delivery, "BilledQuantity") if delivery is not None else None
    settlement = _find(node, "SpecifiedLineTradeSettlement")
    tax = _find(settlement, "ApplicableTradeTax") if settlement is not None else None
    summation = (
        _find(settlement, "SpecifiedTradeSettlementLineMonetarySummation")
        if settlement is not None
        else None
    )
    return {
        "sequence": index,
        "line_id": _text(_find(node, "AssociatedDocumentLineDocument"), "LineID"),
        "product_code": _text(product, "ID"),
        "name": _text(product, "Name"),
        "quantity": _amount(quantity_node.text if quantity_node is not None else None),
        "unit_code": quantity_node.get("unitCode") if quantity_node is not None else None,
        "price_unit": _amount(_text(price, "ChargeAmount")),
        "tax_rate": _amount(_text(tax, "CalculatedRate")),
        "tax_amount": _amount(_text(summation, "TaxTotalAmount")),
        "price_subtotal": _amount(_text(summation, "NetLineTotalAmount")),
        "price_total": _amount(_text(summation, "NetIncludingTaxesLineTotalAmount")),
    }


def validate_root(root, document_type):
    """Validate ``root``, dropping the optional signature first."""
    signature = _find(root, _SIGNATURE_LOCAL)
    if signature is not None:
        root.remove(signature)
    return validator.validate(root, document_type)


def parse(xml_bytes, validate=True):
    """Read ``xml_bytes`` and return the extracted business information.

    The returned dictionary carries the document header, the seller (the
    vendor), the buyer (this company), the currency, the tax buckets, the
    lines and the header totals, plus a validation report.
    """
    root = load(xml_bytes)
    document_type = document_type_of(root)
    errors = validate_root(root, document_type) if validate else []

    document_node = _find(root, "ExchangedDocument")
    transaction = _find(root, "SupplyChainTradeTransaction")
    agreement = _find(transaction, "ApplicableHeaderTradeAgreement")
    settlement = _find(transaction, "ApplicableHeaderTradeSettlement")
    summation = _find(settlement, "SpecifiedTradeSettlementHeaderMonetarySummation")

    return {
        "document_type": document_type,
        "reference": _text(document_node, "ID"),
        "name": _text(document_node, "Name"),
        "type_code": _text(document_node, "TypeCode"),
        "issue_datetime": _text(document_node, "IssueDateTime"),
        "seller": _parse_party(_find(agreement, "SellerTradeParty")),
        "buyer": _parse_party(_find(agreement, "BuyerTradeParty")),
        "currency": _text(settlement, "InvoiceCurrencyCode"),
        "taxes": [_parse_tax(node) for node in _findall(settlement, "ApplicableTradeTax")],
        "lines": [
            _parse_line(node, index)
            for index, node in enumerate(
                _findall(transaction, "IncludedSupplyChainTradeLineItem"), start=1
            )
        ],
        "totals": {
            "line_total": _amount(_text(summation, "LineTotalAmount")),
            "tax_basis_total": _amount(_text(summation, "TaxBasisTotalAmount")),
            "tax_total": _amount(_text(summation, "TaxTotalAmount")),
            "grand_total": _amount(_text(summation, "GrandTotalAmount")),
        },
        "valid": not errors,
        "errors": errors,
    }
