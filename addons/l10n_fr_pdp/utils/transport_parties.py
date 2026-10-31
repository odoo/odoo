"""Compare a Peppol/PDP transport sender with the legal parties of a UBL or CII document."""
import re

LEVEL_NONE = 'none'
LEVEL_WARNING = 'warning'
LEVEL_CRITICAL = 'critical'

# Invoice type codes (UNTDID 1001) for self-billed documents: the sender is the buyer.
SELF_BILLING_TYPE_CODES = {'389', '527', '261'}

# Why the alert was raised, used to build the user message.
REASON_MISSING_PARTIES = 'missing_parties'
REASON_UNCOMPARABLE = 'uncomparable'
REASON_AMBIGUOUS = 'ambiguous'
REASON_SIREN_MISMATCH = 'siren_mismatch'

SIREN_SCHEMES = ('0002', '0009', '0225')
_SIREN_RE = re.compile(r'(\d{9})(?:_.*|\d{5})?$')
_FR_VAT_RE = re.compile(r'FR[0-9A-Z]{2}(\d{9})$')
_PARTY_NODES = {
    'seller': ('AccountingSupplierParty', 'SellerTradeParty'),
    'buyer': ('AccountingCustomerParty', 'BuyerTradeParty'),
}
# EndpointID / URIID are deliberately ignored: the PA already forces them to match the transport
# sender, so only the legal identity (party id, legal entity, VAT) is worth comparing.
_ID_TAGS = ('ID', 'CompanyID')


def clean_value(value):
    return re.sub(r'\s', '', value or '').upper()


def core_value(value):
    """Normalized value without the ISO country prefix of VAT-like numbers (``DK16356706`` -> ``16356706``)."""
    return re.sub(r'^[A-Z]{2}(?=\d)', '', clean_value(value))


def split_identifier(identifier):
    """Split a ``scheme:value`` transport identifier (e.g. ``0225:931473060``)."""
    scheme, sep, value = (identifier or '').partition(':')
    if not sep:
        return '', clean_value(identifier)
    return scheme.strip(), clean_value(value)


def extract_siren(scheme, value):
    """Return the SIREN carried by an identifier, or ``None`` when it cannot be derived."""
    value = clean_value(value)
    scheme = (scheme or '').strip()
    if not value:
        return None
    if scheme in SIREN_SCHEMES:
        match = _SIREN_RE.match(value)
        return match.group(1) if match else None
    if match := _FR_VAT_RE.match(value):
        return match.group(1)
    if re.fullmatch(r'\d{9}|\d{14}', value):
        return value[:9]
    return None


def parse_parties(xml_tree):
    """Read the seller / buyer identifiers and the document type code of a UBL or CII tree.

    :return: ``{'type_code': str, 'seller': [[scheme, value], ...], 'buyer': [[scheme, value], ...]}``
    """
    result = {'type_code': '', 'seller': [], 'buyer': []}
    if xml_tree is None:
        return result
    type_code = xml_tree.xpath(
        "string((//*[local-name()='InvoiceTypeCode' or local-name()='CreditNoteTypeCode']"
        "|//*[local-name()='ExchangedDocument']/*[local-name()='TypeCode'])[1])"
    )
    result['type_code'] = (type_code or '').strip()
    id_xpath = ' or '.join(f"local-name()='{tag}'" for tag in _ID_TAGS)
    for role, node_names in _PARTY_NODES.items():
        party_xpath = ' or '.join(f"local-name()='{name}'" for name in node_names)
        tokens = []
        for party in xml_tree.xpath(f"//*[{party_xpath}]")[:1]:
            for element in party.xpath(f".//*[{id_xpath}]"):
                value = clean_value(element.text)
                token = [(element.get('schemeID') or '').strip(), value]
                if value and token not in tokens:
                    tokens.append(token)
        result[role] = tokens
    return result


def compute_alert(sender, tokens, mandate=False):
    """Compare the transport sender with the XML party identifiers.

    :param sender: transport identifier, e.g. ``0225:931473060``
    :param tokens: list of ``[scheme, value]`` of the compared XML party
    :param mandate: the vendor is allowed to invoice through a third party
    :return: ``(level, reason)``
    """
    sender = (sender or '').strip()
    if not sender or mandate:
        return LEVEL_NONE, False
    if not tokens:
        return LEVEL_WARNING, REASON_MISSING_PARTIES
    sender_scheme, sender_value = split_identifier(sender)
    sender_siren = extract_siren(sender_scheme, sender_value)
    party_sirens = {siren for scheme, value in tokens if (siren := extract_siren(scheme, value))}
    if len(party_sirens) > 1:
        # Several legal entities in one party: could be a crafted file mixing the victim and the sender.
        return LEVEL_WARNING, REASON_AMBIGUOUS
    # Scheme-agnostic match: the XML may carry the national id (or the VAT number) under another scheme.
    if sender_value and sender_value in {core_value(value) for _scheme, value in tokens}:
        return LEVEL_NONE, False
    if not sender_siren or not party_sirens:
        return LEVEL_WARNING, REASON_UNCOMPARABLE
    if sender_siren in party_sirens:
        # Same legal entity (e.g. another establishment): not an impersonation.
        return LEVEL_NONE, False
    return LEVEL_CRITICAL, REASON_SIREN_MISMATCH
