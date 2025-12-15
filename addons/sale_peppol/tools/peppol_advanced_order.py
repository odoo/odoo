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

OrderResponse = {
    '_tag': 'OrderResponse',
    'cbc:CustomizationID': {},
    'cbc:ProfileID': {},
    'cbc:SalesOrderID': {},
    'cbc:ID': {},
    'cbc:IssueDate': {},
    'cbc:OrderResponseCode': {},
    'cbc:Note': {},
    'cbc:DocumentCurrencyCode': {},
    'cbc:CustomerReference': {},
    'cac:OrderReference': {
        'cbc:ID': {},
    },
    'cac:OrderChangeDocumentReference': {
        'cbc:ID': {},
    },
    'cac:SellerSupplierParty': {
        'cac:Party': {
            'cbc:EndpointID': {},
            'cac:PartyIdentification': {
                'cbc:ID': {},
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {},
            },
        },
    },
    'cac:BuyerCustomerParty': cac.CustomerParty,
    'cac:Delivery': {
        'cac:PromisedDeliveryPeriod': {
            'cbc:EndDate': {},
            'cbc:EndTime': {},
        },
    },
    'cac:OrderLine': OrderLine,
}
