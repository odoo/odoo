
DocumentContextParameter = {
    'ram:GuidelineSpecifiedDocumentContextParameter': {
        'ram:ID': {},
    }
}

DateTimeString = {
    'udt:DateTimeString': {},
}

ExchangedDocument = {
    'ram:ID': {},
    'ram:TypeCode': {},
    'ram:IssueDateTime': DateTimeString,
    'ram:IncludedNote': {
        'ram:Content': {},
    },
}

BillingPeriod = {
    'ram:StartDateTime': DateTimeString,
    'ram:EndDateTime': DateTimeString,
}

LineItem = {
    'ram:AssociatedDocumentLineDocument': {
        'ram:LineID': {},
    },
    'ram:SpecifiedTradeProduct': {
        'ram:GlobalID': {},
        'ram:SellerAssignedID': {},
        'ram:Name': {},
        'ram:Description': {},
    },
    'ram:SpecifiedLineTradeAgreement': {
        'ram:GrossPriceProductTradePrice': {
            'ram:ChargeAmount': {},
            'ram:AppliedTradeAllowanceCharge': {
                'ram:ChargeIndicator': {
                    'udt:Indicator': {},
                },
                'ram:ActualAmount': {},
            },
        },
        'ram:NetPriceProductTradePrice': {
            'ram:ChargeAmount': {},
        },
    },
    'ram:SpecifiedLineTradeDelivery': {
        'ram:BilledQuantity': {},
    },
    'ram:SpecifiedLineTradeSettlement': {
        'ram:ApplicableTradeTax': {
            'ram:TypeCode': {},
            'ram:CategoryCode': {},
            'ram:RateApplicablePercent': {},
        },
        'ram:BillingSpecifiedPeriod': BillingPeriod,
        'ram:SpecifiedTradeAllowanceCharge': {
            'ram:ChargeIndicator': {
                'udt:Indicator': {},
            },
            'ram:ActualAmount': {},
            'ram:ReasonCode': {},
            'ram:Reason': {},
        },
        'ram:SpecifiedTradeSettlementLineMonetarySummation': {
            'ram:LineTotalAmount': {},
        },
    },
}

PartnerParty = {
    'ram:ID': {},
    'ram:Name': {},
    'ram:SpecifiedLegalOrganization': {
        'ram:ID': {},
    },
    'ram:DefinedTradeContact': {
        'ram:PersonName': {},
        'ram:TelephoneUniversalCommunication': {
            'ram:CompleteNumber': {},
        },
        'ram:EmailURIUniversalCommunication': {
            'ram:URIID': {},
        },
    },
    'ram:PostalTradeAddress': {
        'ram:PostcodeCode': {},
        'ram:LineOne': {},
        'ram:LineTwo': {},
        'ram:CityName': {},
        'ram:CountryID': {},
    },
}

SellerParty = {
    **PartnerParty,
    'ram:URIUniversalCommunication': {
        'ram:URIID': {},
    },
    'ram:SpecifiedTaxRegistration': {
        'ram:ID': {},
    },
}

BuyerParty = {
    **PartnerParty,
    'ram:URIUniversalCommunication': {
        'ram:URIID': {},
    },
    'ram:SpecifiedTaxRegistration': {
        'ram:ID': {},
    },
}

SupplyChainTrade = {
    'ram:IncludedSupplyChainTradeLineItem': LineItem,
    'ram:ApplicableHeaderTradeAgreement': {
        'ram:BuyerReference': {},
        'ram:SellerTradeParty': SellerParty,
        'ram:BuyerTradeParty': BuyerParty,
        'ram:BuyerOrderReferencedDocument': {
            'ram:IssuerAssignedID': {},
        },
        'ram:ContractReferencedDocument': {
            'ram:IssuerAssignedID': {},
        },
    },
    'ram:ApplicableHeaderTradeDelivery': {
        'ram:ShipToTradeParty': PartnerParty,
        'ram:ActualDeliverySupplyChainEvent': {
            'ram:OccurrenceDateTime': DateTimeString,
        },
    },
    'ram:ApplicableHeaderTradeSettlement': {
        'ram:PaymentReference': {},
        'ram:InvoiceCurrencyCode': {},
        'ram:SpecifiedTradeSettlementPaymentMeans': {
            'ram:TypeCode': {},
            'ram:PayeePartyCreditorFinancialAccount': {
                'ram:IBANID': {},
                'ram:ProprietaryID': {},
            },
        },
        'ram:ApplicableTradeTax': {
            'ram:CalculatedAmount': {},
            'ram:TypeCode': {},
            'ram:ExemptionReason': {},
            'ram:BasisAmount': {},
            'ram:CategoryCode': {},
            'ram:ExemptionReasonCode': {},
            'ram:DueDateTypeCode': {},
            'ram:RateApplicablePercent': {},
        },
        'ram:BillingSpecifiedPeriod': BillingPeriod,
        'ram:SpecifiedTradePaymentTerms': {
            'ram:Description': {},
            'ram:DueDateDateTime': DateTimeString,
            'ram:ApplicableTradePaymentDiscountTerms': {
                'ram:BasisPeriodMeasure': {},
                'ram:CalculationPercent': {},
            },
        },
        'ram:SpecifiedTradeSettlementHeaderMonetarySummation': {
            'ram:LineTotalAmount': {},
            'ram:TaxBasisTotalAmount': {},
            'ram:TaxTotalAmount': {},
            'ram:RoundingAmount': {},
            'ram:GrandTotalAmount': {},
            'ram:TotalPrepaidAmount': {},
            'ram:DuePayableAmount': {},
        },
    },
}

CrossIndustryInvoice = {
    '_tag': 'rsm:CrossIndustryInvoice',
    'rsm:ExchangedDocumentContext': DocumentContextParameter,
    'rsm:ExchangedDocument': ExchangedDocument,
    'rsm:SupplyChainTradeTransaction': SupplyChainTrade,
}
