# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Read a UBL 2.1 or UN/CEFACT CII (Factur-X) invoice tree into a plain dict."""
from datetime import datetime

NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'rsm': 'urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100',
    'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
    'udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataTypes:100',
}
CREDIT_NOTE_TYPE_CODES = {'381', '261', '262', '396', '502', '503'}


def detect_syntax(xml_tree):
    """Return ``ubl``, ``cii`` or ``False``."""
    if xml_tree is None:
        return False
    local_name = xml_tree.tag.rsplit('}', 1)[-1] if isinstance(xml_tree.tag, str) else ''
    if local_name in ('Invoice', 'CreditNote'):
        return 'ubl'
    if local_name == 'CrossIndustryInvoice':
        return 'cii'
    return False


def read_invoice(xml_tree):
    """Return a dict (see ``_empty_result``) or ``False`` when the tree is not a supported invoice."""
    syntax = detect_syntax(xml_tree)
    if not syntax:
        return False
    result = _read_ubl(xml_tree) if syntax == 'ubl' else _read_cii(xml_tree)
    result['syntax'] = 'facturx' if syntax == 'cii' and _cii_is_facturx(xml_tree) else syntax
    result['is_credit_note'] = (
        xml_tree.tag.endswith('}CreditNote') or result['type_code'] in CREDIT_NOTE_TYPE_CODES
    )
    return result


def _empty_result():
    return {
        'syntax': False, 'number': '', 'type_code': '', 'issue_date': '', 'due_date': '', 'currency': '',
        'is_credit_note': False, 'notes': [], 'seller': {}, 'buyer': {}, 'delivery': {}, 'payee': {},
        'lines': [], 'taxes': [], 'totals': {}, 'payment_terms': '', 'payment_means_code': '',
        'payment_means_name': '', 'payment_reference': '', 'ibans': [],
    }


def _empty_party():
    return {
        'name': '', 'street': '', 'zip': '', 'city': '', 'country': '',
        'vat': '', 'legal_id': '', 'email': '', 'phone': '',
    }


def _text(node, path):
    if node is None:
        return ''
    found = node.find(path, NS)
    return (found.text or '').strip() if found is not None else ''


def _texts(node, path):
    return [(found.text or '').strip() for found in node.findall(path, NS) if (found.text or '').strip()]


def _cii_date(node, path):
    value = _text(node, path)
    # Factur-X uses UnqualifiedDataType (singular); some files use the plural URI.
    if not value and node is not None and '/' in path:
        parent = node.find(path.rsplit('/', 1)[0], NS)
        if parent is not None:
            found = parent.find('{*}DateTimeString')
            value = (found.text or '').strip() if found is not None else ''
    if len(value) == 8 and value.isdigit():
        try:
            return datetime.strptime(value, '%Y%m%d').date().isoformat()
        except ValueError:
            pass
    return value


def _cii_is_facturx(root):
    guideline = _text(
        root, 'rsm:ExchangedDocumentContext/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID',
    ).lower()
    return 'factur-x' in guideline or 'zugferd' in guideline


def _ubl_party(party):
    if party is None:
        return {}
    values = _empty_party()
    values.update({
        'name': _text(party, 'cac:PartyLegalEntity/cbc:RegistrationName') or _text(party, 'cac:PartyName/cbc:Name'),
        'street': ' '.join(filter(None, [
            _text(party, 'cac:PostalAddress/cbc:StreetName'),
            _text(party, 'cac:PostalAddress/cbc:AdditionalStreetName'),
        ])),
        'zip': _text(party, 'cac:PostalAddress/cbc:PostalZone'),
        'city': _text(party, 'cac:PostalAddress/cbc:CityName'),
        'country': _text(party, 'cac:PostalAddress/cac:Country/cbc:IdentificationCode'),
        'vat': _text(party, 'cac:PartyTaxScheme/cbc:CompanyID'),
        'legal_id': _text(party, 'cac:PartyLegalEntity/cbc:CompanyID'),
        'email': _text(party, 'cac:Contact/cbc:ElectronicMail'),
        'phone': _text(party, 'cac:Contact/cbc:Telephone'),
    })
    return values


def _ubl_address(address, name=''):
    if address is None and not name:
        return {}
    values = _empty_party()
    values.update({
        'name': name,
        'street': ' '.join(filter(None, [
            _text(address, 'cbc:StreetName'),
            _text(address, 'cbc:AdditionalStreetName'),
        ])),
        'zip': _text(address, 'cbc:PostalZone'),
        'city': _text(address, 'cbc:CityName'),
        'country': _text(address, 'cac:Country/cbc:IdentificationCode'),
    })
    return values


def _ubl_delivery(root):
    delivery = root.find('cac:Delivery', NS)
    if delivery is None:
        return {}
    party = _ubl_party(delivery.find('cac:DeliveryParty', NS))
    location = _ubl_address(
        delivery.find('cac:DeliveryLocation/cac:Address', NS),
        name=_text(delivery, 'cac:DeliveryLocation/cbc:ID'),
    ) or _ubl_address(delivery.find('cac:DeliveryAddress', NS))
    if not party:
        return location
    # The party often carries only the name; the postal address sits on DeliveryLocation.
    for key in ('name', 'street', 'zip', 'city', 'country'):
        if not party.get(key) and location.get(key):
            party[key] = location[key]
    return party


def _read_ubl(root):
    result = _empty_result()
    result.update({
        'number': _text(root, 'cbc:ID'),
        'type_code': _text(root, 'cbc:InvoiceTypeCode') or _text(root, 'cbc:CreditNoteTypeCode'),
        'issue_date': _text(root, 'cbc:IssueDate'),
        'due_date': _text(root, 'cbc:DueDate') or _text(root, 'cac:PaymentMeans/cbc:PaymentDueDate'),
        'currency': _text(root, 'cbc:DocumentCurrencyCode'),
        'notes': _texts(root, 'cbc:Note'),
        'seller': _ubl_party(root.find('cac:AccountingSupplierParty/cac:Party', NS)),
        'buyer': _ubl_party(root.find('cac:AccountingCustomerParty/cac:Party', NS)),
        'delivery': _ubl_delivery(root),
        'payee': _ubl_party(root.find('cac:PayeeParty', NS)),
        'payment_terms': _text(root, 'cac:PaymentTerms/cbc:Note'),
        'payment_reference': _text(root, 'cac:PaymentMeans/cbc:PaymentID'),
        'ibans': _texts(root, 'cac:PaymentMeans/cac:PayeeFinancialAccount/cbc:ID'),
    })
    means = root.find('cac:PaymentMeans/cbc:PaymentMeansCode', NS)
    if means is not None:
        result['payment_means_code'] = (means.text or '').strip()
        result['payment_means_name'] = (means.get('name') or '').strip()
    for line in root.findall('cac:InvoiceLine', NS) + root.findall('cac:CreditNoteLine', NS):
        quantity_node = line.find('cbc:InvoicedQuantity', NS)
        if quantity_node is None:
            quantity_node = line.find('cbc:CreditedQuantity', NS)
        result['lines'].append({
            'name': _text(line, 'cac:Item/cbc:Name'),
            'description': _text(line, 'cac:Item/cbc:Description'),
            'quantity': (quantity_node.text or '').strip() if quantity_node is not None else '',
            'unit': quantity_node.get('unitCode', '') if quantity_node is not None else '',
            'price_unit': _text(line, 'cac:Price/cbc:PriceAmount'),
            'tax_percent': _text(line, 'cac:Item/cac:ClassifiedTaxCategory/cbc:Percent'),
            'subtotal': _text(line, 'cbc:LineExtensionAmount'),
        })
    for subtotal in root.findall('cac:TaxTotal/cac:TaxSubtotal', NS):
        result['taxes'].append({
            'percent': _text(subtotal, 'cac:TaxCategory/cbc:Percent'),
            'base': _text(subtotal, 'cbc:TaxableAmount'),
            'amount': _text(subtotal, 'cbc:TaxAmount'),
        })
    monetary = root.find('cac:LegalMonetaryTotal', NS)
    result['totals'] = {
        'untaxed': _text(monetary, 'cbc:TaxExclusiveAmount') or _text(monetary, 'cbc:LineExtensionAmount'),
        'tax': _text(root, 'cac:TaxTotal/cbc:TaxAmount'),
        'total': _text(monetary, 'cbc:TaxInclusiveAmount'),
        'prepaid': _text(monetary, 'cbc:PrepaidAmount'),
        'due': _text(monetary, 'cbc:PayableAmount'),
    }
    return result


def _cii_party(party):
    if party is None:
        return {}
    values = _empty_party()
    values.update({
        'name': _text(party, 'ram:Name'),
        'street': ' '.join(filter(None, [
            _text(party, 'ram:PostalTradeAddress/ram:LineOne'),
            _text(party, 'ram:PostalTradeAddress/ram:LineTwo'),
        ])),
        'zip': _text(party, 'ram:PostalTradeAddress/ram:PostcodeCode'),
        'city': _text(party, 'ram:PostalTradeAddress/ram:CityName'),
        'country': _text(party, 'ram:PostalTradeAddress/ram:CountryID'),
        'vat': _text(party, "ram:SpecifiedTaxRegistration/ram:ID[@schemeID='VA']")
        or _text(party, 'ram:SpecifiedTaxRegistration/ram:ID'),
        'legal_id': _text(party, 'ram:SpecifiedLegalOrganization/ram:ID'),
        'email': _cii_email(party),
        'phone': _text(party, 'ram:DefinedTradeContact/ram:TelephoneUniversalCommunication/ram:CompleteNumber'),
    })
    return values


def _cii_email(party):
    """Contact email. The party URIID is an electronic address (often scheme 0225), not a mailbox."""
    contact = _text(party, 'ram:DefinedTradeContact/ram:EmailURIUniversalCommunication/ram:URIID')
    if contact:
        return contact
    endpoint = _text(party, 'ram:URIUniversalCommunication/ram:URIID')
    return endpoint if '@' in endpoint else ''


def _read_cii(root):
    result = _empty_result()
    document = root.find('rsm:ExchangedDocument', NS)
    transaction = root.find('rsm:SupplyChainTradeTransaction', NS)
    agreement = transaction.find('ram:ApplicableHeaderTradeAgreement', NS) if transaction is not None else None
    settlement = transaction.find('ram:ApplicableHeaderTradeSettlement', NS) if transaction is not None else None
    terms = settlement.find('ram:SpecifiedTradePaymentTerms', NS) if settlement is not None else None
    summation = (
        settlement.find('ram:SpecifiedTradeSettlementHeaderMonetarySummation', NS) if settlement is not None else None
    )
    result.update({
        'number': _text(document, 'ram:ID'),
        'type_code': _text(document, 'ram:TypeCode'),
        'issue_date': _cii_date(document, 'ram:IssueDateTime/udt:DateTimeString'),
        'due_date': _cii_date(terms, 'ram:DueDateDateTime/udt:DateTimeString'),
        'currency': _text(settlement, 'ram:InvoiceCurrencyCode'),
        'notes': _texts(document, 'ram:IncludedNote/ram:Content') if document is not None else [],
        'seller': _cii_party(agreement.find('ram:SellerTradeParty', NS) if agreement is not None else None),
        'buyer': _cii_party(agreement.find('ram:BuyerTradeParty', NS) if agreement is not None else None),
        'delivery': _cii_party(
            transaction.find('ram:ApplicableHeaderTradeDelivery/ram:ShipToTradeParty', NS)
            if transaction is not None else None
        ),
        'payee': _cii_party(settlement.find('ram:PayeeTradeParty', NS) if settlement is not None else None),
        'payment_terms': _text(terms, 'ram:Description'),
    })
    if settlement is not None:
        means = settlement.find('ram:SpecifiedTradeSettlementPaymentMeans', NS)
        result['payment_means_code'] = _text(means, 'ram:TypeCode')
        result['payment_means_name'] = _text(means, 'ram:Information')
        # Factur-X puts BT-83 on the settlement; some CII files put it on the means.
        result['payment_reference'] = (
            _text(settlement, 'ram:PaymentReference') or _text(means, 'ram:PaymentReference')
        )
        accounts = _texts(
            settlement,
            'ram:SpecifiedTradeSettlementPaymentMeans/ram:PayeePartyCreditorFinancialAccount/ram:IBANID',
        )
        for value in _texts(
            settlement,
            'ram:SpecifiedTradeSettlementPaymentMeans/ram:PayeePartyCreditorFinancialAccount/ram:ProprietaryID',
        ):
            if value not in accounts:
                accounts.append(value)
        result['ibans'] = accounts
        for tax in settlement.findall('ram:ApplicableTradeTax', NS):
            result['taxes'].append({
                'percent': _text(tax, 'ram:RateApplicablePercent'),
                'base': _text(tax, 'ram:BasisAmount'),
                'amount': _text(tax, 'ram:CalculatedAmount'),
            })
    line_items = transaction.findall('ram:IncludedSupplyChainTradeLineItem', NS) if transaction is not None else []
    for line in line_items:
        quantity_node = line.find('ram:SpecifiedLineTradeDelivery/ram:BilledQuantity', NS)
        line_settlement = 'ram:SpecifiedLineTradeSettlement'
        result['lines'].append({
            'name': _text(line, 'ram:SpecifiedTradeProduct/ram:Name'),
            'description': _text(line, 'ram:SpecifiedTradeProduct/ram:Description'),
            'quantity': (quantity_node.text or '').strip() if quantity_node is not None else '',
            'unit': quantity_node.get('unitCode', '') if quantity_node is not None else '',
            'price_unit': _text(line, 'ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:ChargeAmount'),
            'tax_percent': _text(line, '%s/ram:ApplicableTradeTax/ram:RateApplicablePercent' % line_settlement),
            'subtotal': _text(
                line,
                '%s/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount' % line_settlement,
            ),
        })
    result['totals'] = {
        'untaxed': _text(summation, 'ram:TaxBasisTotalAmount') or _text(summation, 'ram:LineTotalAmount'),
        'tax': _text(summation, 'ram:TaxTotalAmount'),
        'total': _text(summation, 'ram:GrandTotalAmount'),
        'prepaid': _text(summation, 'ram:TotalPrepaidAmount'),
        'due': _text(summation, 'ram:DuePayableAmount'),
    }
    return result
