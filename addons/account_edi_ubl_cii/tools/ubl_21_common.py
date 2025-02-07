# This file contains dicts defining the order of nodes of UBL 2.1 elements.
# These are the elements used in the Invoice, CreditNote, DebitNote and Order documents.

# If you need to use a new element, you should define it below so that it will be added at the
# correct place in the XML.

Period = {
    'cbc:StartDate': {},
    'cbc:EndDate': {},
    'cbc:DescriptionCode': {},
    'cbc:Description': {},
}

DiscrepancyResponse = {
    'cbc:ReferenceID': {},
    'cbc:ResponseCode': {},
    'cbc:Description': {},
}

OrderReference = {
    'cbc:ID': {},
    'cbc:SalesOrderID': {},
    'cbc:IssueDate': {},
}

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

DocumentReference = {
    'cbc:ID': {},
    'cbc:UUID': {},
    'cbc:IssueDate': {},
    'cbc:IssueTime': {},
    'cbc:DocumentTypeCode': {},
    'cbc:DocumentType': {},
    'cbc:DocumentDescription': {},
    'cac:Attachment': Attachment,
}

BillingReference = {
    'cac:InvoiceDocumentReference': DocumentReference,
}

Signature = {
    'cbc:ID': {},
    'cbc:SignatureMethod': {},
    'cac:SignatoryParty': {
        'cac:PartyIdentification': {
            'cbc:ID': {}
        },
        'cac:PartyName': {
            'cbc:Name': {},
        }
    },
    'cac:DigitalSignatureAttachment': {
        'cac:ExternalReference': {
            'cbc:URI': {},
        }
    }
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
    'cac:Country': {
        'cbc:IdentificationCode': {},
        'cbc:Name': {},
    },
}

Contact = {
    'cbc:ID': {},
    'cbc:Name': {},
    'cbc:Telephone': {},
    'cbc:ElectronicMail': {},
}

PowerOfAttorney = {
    'cac:AgentParty': {
        'cac:PartyIdentification': {
            'cbc:ID': {}
        },
    },
}

Party = {
    'cbc:EndpointID': {},
    'cbc:IndustryClassificationCode': {},
    'cac:PartyIdentification': {
        'cbc:ID': {},
    },
    'cac:PartyName': {
        'cbc:Name': {},
    },
    'cac:PhysicalLocation': {
        'cac:Address': Address,
    },
    'cac:PostalAddress': Address,
    'cac:PartyTaxScheme': {
        'cbc:RegistrationName': {},
        'cbc:CompanyID': {},
        'cbc:TaxLevelCode': {},
        'cac:RegistrationAddress': Address,
        'cac:TaxScheme': {
            'cbc:ID': {},
            'cbc:Name': {},
        },
    },
    'cac:PartyLegalEntity': {
        'cbc:RegistrationName': {},
        'cbc:CompanyID': {},
        'cac:RegistrationAddress': Address,
    },
    'cac:Contact': Contact,
    'cac:Person': {
        'cbc:FirstName': {},
        'cbc:FamilyName': {},
    },
    'cac:PowerOfAttorney': PowerOfAttorney,
}

SupplierParty = {
    'cbc:CustomerAssignedAccountID': {},
    'cbc:AdditionalAccountID': {},
    'cac:Party': Party,
    'cac:AccountingContact': Contact,
}

CustomerParty = {
    'cbc:AdditionalAccountID': {},
    'cac:Party': Party,
    'cac:AccountingContact': Contact,
}

Delivery = {
    'cbc:ID': {},
    'cbc:ActualDeliveryDate': {},
    'cac:DeliveryLocation': {
        'cac:Address': Address,
    },
    'cac:DeliveryParty': Party,
}

FinancialAccount = {
    'cbc:ID': {},
    'cac:FinancialInstitutionBranch': {
        'cbc:ID': {},
        'cac:FinancialInstitution': {
            'cbc:ID': {},
            'cbc:Name': {},
            'cac:Address': Address,
        }
    }
}

PaymentMeans = {
    'cbc:ID': {},
    'cbc:PaymentMeansCode': {},
    'cbc:PaymentDueDate': {},
    'cbc:InstructionID': {},
    'cbc:InstructionNote': {},
    'cbc:PaymentID': {},
    'cac:PayeeFinancialAccount': FinancialAccount,
}

PaymentTerms = {
    'cbc:ID': {},
    'cbc:PaymentMeansID': {},
    'cbc:Note': {},
    'cbc:PaymentPercent': {},
    'cbc:Amount': {},
    'cbc:PaymentDueDate': {},
    'cac:SettlementPeriod': Period,
}

PrepaidPayment = {
    'cbc:ID': {},
    'cbc:PaidAmount': {},
    'cbc:ReceivedDate': {},
}

ExchangeRate = {
    'cbc:SourceCurrencyCode': {},
    'cbc:SourceCurrencyBaseRate': {},
    'cbc:TargetCurrencyCode': {},
    'cbc:TargetCurrencyBaseRate': {},
    'cbc:CalculationRate': {},
    'cbc:Date': {},
}

TaxCategory = {
    'cbc:ID': {},
    'cbc:Name': {},
    'cbc:Percent': {},
    'cbc:TaxExemptionReasonCode': {},
    'cbc:TaxExemptionReason': {},
    'cbc:TierRange': {},
    'cac:TaxScheme': {
        'cbc:ID': {},
        'cbc:Name': {},
        'cbc:TaxTypeCode': {},
    },
}

AllowanceCharge = {
    'cbc:ChargeIndicator': {},
    'cbc:AllowanceChargeReasonCode': {},
    'cbc:AllowanceChargeReason': {},
    'cbc:MultiplierFactorNumeric': {},
    'cbc:Amount': {},
    'cbc:BaseAmount': {},
    'cac:TaxCategory': TaxCategory,
}

TaxTotal = {
    'cbc:TaxAmount': {},
    'cbc:RoundingAmount': {},
    'cac:TaxSubtotal': {
        'cbc:TaxableAmount': {},
        'cbc:TaxAmount': {},
        'cbc:BaseUnitMeasure': {},
        'cbc:PerUnitAmount': {},
        'cbc:Percent': {},
        'cac:TaxCategory': TaxCategory,
    }
}

MonetaryTotal = {
    'cbc:LineExtensionAmount': {},
    'cbc:TaxExclusiveAmount': {},
    'cbc:TaxInclusiveAmount': {},
    'cbc:AllowanceTotalAmount': {},
    'cbc:ChargeTotalAmount': {},
    'cbc:PrepaidAmount': {},
    'cbc:PayableAmount': {},
}

OrderLineReference = {
    'cbc:LineID': {},
}

PricingReference = {
    'cac:AlternativeConditionPrice': {
        'cbc:PriceAmount': {},
        'cbc:PriceTypeCode': {},
    }
}

ItemIdentification = {
    'cbc:ID': {},
    'cbc:ExtendedID': {},
}

Item = {
    'cbc:Description': {},
    'cbc:Name': {},
    'cbc:BrandName': {},
    'cbc:ModelName': {},
    'cac:BuyersItemIdentification': ItemIdentification,
    'cac:SellersItemIdentification': ItemIdentification,
    'cac:StandardItemIdentification': ItemIdentification,
    'cac:CommodityClassification': {
        'cbc:ItemClassificationCode': {},
    },
    'cac:ClassifiedTaxCategory': TaxCategory,
    'cac:AdditionalItemProperty': {
        'cbc:Name': {},
        'cbc:Value': {},
    },
    'cac:InformationContentProviderParty': Party,
}

Price = {
    'cbc:PriceAmount': {},
    'cbc:BaseQuantity': {},
    'cac:AllowanceCharge': AllowanceCharge
}

ItemPriceExtension = {
    'cbc:Amount': {},
}
