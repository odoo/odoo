# The Invoice dict defines the structure of a UBL TR Invoice, with all nodes in the correct order.
# It can be passed as the `template` argument to `clean_dict_nodes` and then  `dict_to_xml` to
# enforce the order of nodes. The TR Invoice dict is a created as a seperate dict than the UBL 2.1
# and cleaned, since Turkey follows UBL 1.2.

import odoo.addons.l10n_tr_nilvera_einvoice_extended.tools.ubl_tr_common as cac

TrInvoiceLine = {
    'cbc:ID': {},
    'cbc:Note': {},
    'cbc:InvoicedQuantity': {},
    'cbc:LineExtensionAmount': {},
    'cac:OrderLineReference': cac.OrderLineReference,
    'cac:DespatchLineReference': cac.BillingReference,
    'cac:ReceipitReference': cac.BillingReference,
    'cac:Delivery': cac.Delivery,
    'cac:AllowanceCharge': cac.AllowanceCharge,
    'cac:TaxTotal': cac.TaxTotal,
    'cac:WithholdingTaxTotal': cac.TaxTotal,
    'cac:Item': cac.Item,
    'cac:Price': cac.Price,
}

TrInvoice = {
    '_tag': 'Invoice',
    'ext:UBLExtensions': {},
    'cbc:UBLVersionID': {},
    'cbc:CustomizationID': {},
    'cbc:ProfileID': {},
    'cbc:ProfileExecutionID': {},
    'cbc:ID': {},
    'cbc:CopyIndicator': {},
    'cbc:UUID': {},
    'cbc:IssueDate': {},
    'cbc:IssueTime': {},
    'cbc:DueDate': {},
    'cbc:InvoiceTypeCode': {},
    'cbc:Note': {},
    'cbc:DocumentCurrencyCode': {},
    'cbc:TaxCurrencyCode': {},
    'cbc:PricingCurrencyCode': {},
    'cbc:LineCountNumeric': {},
    'cbc:BuyerReference': {},
    'cac:InvoicePeriod': cac.Period,
    'cac:OrderReference': cac.OrderReference,
    'cac:BillingReference': cac.BillingReference,
    'cac:AdditionalDocumentReference': cac.DocumentReference,
    'cac:Signature': cac.Signature,
    'cac:AccountingSupplierParty': cac.SupplierParty,
    'cac:AccountingCustomerParty': cac.CustomerParty,
    'cac:SellerSupplierParty': cac.SupplierParty,
    'cac:BuyerCustomerParty': cac.CustomerParty,
    'cac:Delivery': cac.Delivery,
    'cac:PaymentMeans': cac.PaymentMeans,
    'cac:PaymentTerms': cac.PaymentTerms,
    'cac:AllowanceCharge': cac.AllowanceCharge,
    'cac:TaxExchangeRate': cac.ExchangeRate,
    'cac:PricingExchangeRate': cac.ExchangeRate,
    'cac:PaymentExchangeRate': cac.ExchangeRate,
    'cac:TaxTotal': cac.TaxTotal,
    'cac:WithholdingTaxTotal': cac.TaxTotal,
    'cac:LegalMonetaryTotal': cac.MonetaryTotal,
    'cac:InvoiceLine': TrInvoiceLine,
}
