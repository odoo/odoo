# This file contains dicts defining the order of nodes of UBL 1.2 elements.
# These are the elements used in the Invoice, CreditNote, DebitNote, Distpatch and Order documents.

# If you need to use a new element, you should define it below so that it will be added at the
# correct place in the XML.

Attachment = {
    'cbc:EmbeddedDocumentBinaryObject': {},
    'cac:ExternalReference': {
        'cbc:URI': {},
        'cbc:MimeCode': {},
        'cbc:EncodingCode': {},
        'cbc:FileName': {},
        'cbc:Description': {},
    },
}

Branch = {
    'cbc:Name': {},
    'cac:FinancialInstitution': {
        'cbc:Name': {},
    },
}

CommodityClassification = {
    'cbc:ItemClassificationCode': {},
}

Country = {
    'cbc:IdentificationCode': {},
    'cbc:Name': {},
}

Contact = {
    'cbc:Telephone': {},
    'cbc:ElectronicMail': {},
    'cbc:Telefax': {},
}

DocumentReference = {
    'cbc:AttributeID': {},
    'cbc:Measure': {},
    'cbc:Description': {},
    'cbc:MinimumMeasure': {},
    'cbc:MaximumMeasure': {},
}

Price = {
    'cbc:PriceAmount': {},
}

Period = {
    'cbc:StartDate': {},
    'cbc:StartTime': {},
    'cbc:EndDate': {},
    'cbc:EndTime': {},
    'cbc:DurationMeasure': {},
    'cbc:Description': {},
}

OrderReference = {
    'cbc:ID': {},
    'cbc:SalesOrderID': {},
    'cbc:IssueDate': {},
    'cbc:DocumentReference': {},
}

Address = {
    'cbc:ID': {},
    'cbc:AddressTypeCode': {},
    'cbc:AddressFormatCode': {},
    'cbc:StreetName': {},
    'cbc:AdditionalStreetName': {},
    'cbc:BuildingName': {},
    'cbc:BuildingNumber': {},
    'cbc:PlotIdentification': {},
    'cbc:CitySubdivisionName': {},
    'cbc:CityName': {},
    'cbc:PostalZone': {},
    'cbc:CountrySubentity': {},
    'cbc:CountrySubentityCode': {},
    'cac:AddressLine': {
        'cbc:Line': {},
    },
    'cac:Country': Country,
}

BillingReference = {
    'cac:InvoiceDocumentReference': DocumentReference,
}

IssuerParty = {
    'cbc:EndpointID': {},
    'cac:PartyIdentification': {
        'cbc:ID': {},
    },
    'cac:PostalAddress': Address,
}

DocumentReference = {
    'cbc:ID': {},
    'cbc:UUID': {},
    'cbc:IssueDate': {},
    'cbc:IssueTime': {},
    'cbc:DocumentTypeCode': {},
    'cbc:DocumentStatusCode': {},
    'cbc:DocumentType': {},
    'cbc:DocumentDescription': {},
    'cac:Attachment': Attachment,
    'cac:IssuerParty': IssuerParty,
}

Signature = {
    'cbc:ID': {},
    'cbc:SignatureMethod': {},
    'cac:SignatoryParty': {
        'cac:PartyIdentification': {
            'cbc:ID': {},
        },
        'cac:PostalAddress': Address,
        'cac:PartyName': {
            'cbc:Name': {},
        },
    },
    'cac:DigitalSignatureAttachment': {
        'cac:ExternalReference': {
            'cbc:URI': {},
        },
    },
}

FinancialAccount = {
    'cbc:ID': {},
    'cbc:CurrencyCode': {},
    'cbc:PaymentNote': {},
    'cac:FinancialInstitutionBranch': Branch,
}

Person = {
    'cbc:FirstName': {},
    'cbc:FamilyName': {},
    'cbc:Title': {},
    'cbc:MiddleName': {},
    'cbc:NameSuffix': {},
    'cbc:NationID': {},
    'cac:FinancialAccount': FinancialAccount,
    'cac:IdentityDocumentReference': DocumentReference,
}

CorporateRegistrationScheme = {
    'cbc:ID': {},
    'cbc:Name': {},
    'cbc:CorporateRegistrationTypeCode': {},
    'cac:JuridictionRegionAddress': Address,
}

Party = {
    'cbc:WebsiteURL': {},
    'cbc:EndpointID': {},
    'cbc:IndustryClassificationCode': {},
    'cac:PartyIdentification': {
        'cbc:ID': {},
    },
    'cac:PartyName': {
        'cbc:Name': {},
    },
    'cac:PostalAddress': Address,
    'cac:PhysicalLocation': Address,
    'cac:PartyTaxScheme': {
        'cac:TaxScheme': {
            'cbc:Name': {},
        },
    },
    'cac:PartyLegalEntity': {
        'cbc:RegistrationName': {},
        'cbc:CompanyID': {},
        'cbc:RegistrationDate': {},
        'cbc:SoleProprietorshipIndicator': {},
        'cbc:CorporateStockAmount': {},
        'cbc:FullyPaidSharesIndicator': {},
        'cac:CorporateRegistrationScheme': CorporateRegistrationScheme,
        'cac:HeadOfficeParty': {
            'cac:PartyIdentification': {
                'cbc:ID': {},
            },
            'cac:PostalAddress': Address,
        },
    },
    'cac:Contact': Contact,
    'cac:Person': Person,
}


SupplierParty = {
    'cac:Party': Party,
    'cac:DespatchContact': Contact,
}

CustomerParty = {
    'cac:Party': Party,
    'cac:DeliveryContact': Contact,
}

DeliveryTerms = {
    'cbc:ID': {},
    'cbc:SpecialTerms': {},
    'cbc:Amount': {},
}

Despatch = {
    'cbc:ID': {},
    'cbc:ActualDespatchDate': {},
    'cbc:ActualDespatchTime': {},
    'cbc:Insuctions': {},
    'cac:DespatchAddress': Address,
    'cac:DespatchParty': Party,
    'cac:Contact': Contact,
    'cac:EstimatedDespatchPeriod': Period,
}

# cac:shipment has to be fully added here for l10n__nilvera_edispatch to be integrated with E-Invoicing
# l10n__nilvera_edispatch.xml template has to be removed.
GoodsItem = {
    'cbc:RequiredCustomsID': {},
}

ShipmentStage = {
    'cbc:TransportModeCode': {},
}

Shippment = {
    'cbc:ID': {},
    'cac:GoodsItem': GoodsItem,
    'cac:ShipmentStage': ShipmentStage,
}

Delivery = {
    'cbc:ID': {},
    'cbc:Quantity': {},
    'cbc:ActualDeliveryDate': {},
    'cbc:ActualDeliveryTime': {},
    'cbc:LatestDeliveryDate': {},
    'cbc:LatestDeliveryTime': {},
    'cbc:ackingID': {},
    'cac:DeliveryAddress': Address,
    'cac:AlternativeDeliveryLocation': Address,
    'cac:EstimatedDeliveryPeriod': Period,
    'cac:CarrierParty': Party,
    'cac:DeliveryParty': Party,
    'cac:Despatch': Despatch,
    'cac:DeliveryTerms': DeliveryTerms,
    'cac:Shipment': Shippment,
}

PaymentMeans = {
    'cbc:PaymentMeansCode': {},
    'cbc:PaymentDueDate': {},
    'cbc:PaymentChannelCode': {},
    'cbc:InsuctionNote': {},
    'cac:PayerFinancialAccount': FinancialAccount,
    'cac:PayeeFinancialAccount': FinancialAccount,
}

PaymentTerms = {
    'cbc:Note': {},
    'cbc:PenaltySurchargePercent': {},
    'cbc:Amount': {},
    'cbc:PenaltyAmount': {},
    'cbc:PaymentDueDate': {},
    'cac:SettlementPeriod': Period,
}

ExchangeRate = {
    'cbc:SourceCurrencyCode': {},
    'cbc:TargetCurrencyCode': {},
    'cbc:CalculationRate': {},
    'cbc:Date': {},
}

TaxCategory = {
    'cbc:Name': {},
    'cbc:TaxExemptionReasonCode': {},
    'cbc:TaxExemptionReason': {},
    'cac:TaxScheme': {
        'cbc:ID': {},
        'cbc:Name': {},
        'cbc:TaxTypeCode': {},
    },
}

AllowanceCharge = {
    'cbc:ChargeIndicator': {},
    'cbc:AllowanceChargeReason': {},
    'cbc:MultiplierFactorNumeric': {},
    'cbc:SequenceNumeric': {},
    'cbc:Amount': {},
    'cbc:BaseAmount': {},
    'cbc:PerUnitAmount': {},
}

TaxTotal = {
    'cbc:TaxAmount': {},
    'cac:TaxSubtotal': {
        'cbc:TaxableAmount': {},
        'cbc:TaxAmount': {},
        'cbc:CalculationSequenceNumeric': {},
        'cbc:ansactionCurrencyTaxAmount': {},
        'cbc:Percent': {},
        'cbc:BaseUnitMeasure': {},
        'cbc:PerUnitAmount': {},
        'cac:TaxCategory': TaxCategory,
    },
}

MonetaryTotal = {
    'cbc:LineExtensionAmount': {},
    'cbc:TaxExclusiveAmount': {},
    'cbc:TaxInclusiveAmount': {},
    'cbc:AllowanceTotalAmount': {},
    'cbc:ChargeTotalAmount': {},
    'cbc:PayableRoundingAmount': {},
    'cbc:PayableAmount': {},
}

OrderLineReference = {
    'cbc:LineID': {},
}

ItemIdentification = {
    'cbc:ID': {},
}

# Any additional Properties for the Item Instance have to be added here
AdditionalItemProperty = {

}

ItemInstance = {
    'cbc:ProductaceID': {},
    'cbc:ManufacturedDate': {},
    'cbc:ManufacturedTime': {},
    'cbc:BestBeforeDate': {},
    'cbc:RegisationID': {},
    'cbc:SerialID': {},
    'cac:AdditionalItemProperty': AdditionalItemProperty,
    'cac:LotIdentification': ItemIdentification,
}

Item = {
    'cbc:Description': {},
    'cbc:Name': {},
    'cbc:Keyword': {},
    'cbc:BrandName': {},
    'cbc:ModelName': {},
    'cac:BuyersItemIdentification': ItemIdentification,
    'cac:SellersItemIdentification': ItemIdentification,
    'cac:StandardItemIdentification': ItemIdentification,
    'cac:ManufacturersItemIdentification': ItemIdentification,
    'cac:AdditionalItemIdentification': ItemIdentification,
    'cac:OriginCountry': Country,
    'cac:CommodityClassification': CommodityClassification,
    'cac:ItemInstance': ItemIdentification,
}
