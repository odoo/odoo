# The Order dict defines the structure of a UBL 2.1 Order, with all nodes in the correct order.
# It can be passed as the `template` argument to `dict_to_xml` to enforce the order of nodes.

import odoo.addons.account_edi_ubl_cii.tools.ubl_21_common as cac

OrderLine = {
    'cac:LineItem': {
        'cbc:ID': {},
        'cbc:UUID': {},
        'cbc:Note': {},
        'cbc:Quantity': {},
        'cbc:LineExtensionAmount': {},
        'cbc:TotalTaxAmount': {},
        'cac:AllowanceCharge': cac.AllowanceCharge,
        'cac:Price': cac.Price,
        'cac:Item': cac.Item,
        'cac:TaxTotal': cac.TaxTotal,
        'cac:ItemPriceExtension': cac.ItemPriceExtension,
    }
}

Order = {
    '_tag': 'Order',
    'cbc:CustomizationID': {},
    'cbc:ProfileID': {},
    'cbc:ID': {},
    'cbc:IssueDate': {},
    'cbc:OrderTypeCode': {},
    'cbc:Note': {},
    'cbc:DocumentCurrencyCode': {},
    'cac:ValidityPeriod': cac.Period,
    'cac:QuotationDocumentReference': cac.DocumentReference,
    'cac:OriginatorDocumentReference': cac.DocumentReference,
    'cac:BuyerCustomerParty': cac.CustomerParty,
    'cac:SellerSupplierParty': cac.SupplierParty,
    'cac:Delivery': cac.Delivery,
    'cac:PaymentTerms': cac.PaymentTerms,
    'cac:AllowanceCharge': cac.AllowanceCharge,
    'cac:TaxTotal': cac.TaxTotal,
    'cac:AnticipatedMonetaryTotal': cac.MonetaryTotal,
    'cac:OrderLine': OrderLine,
}
