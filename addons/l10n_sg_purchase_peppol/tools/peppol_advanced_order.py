Order = {
    "_tag": "Order",
    "cbc:CustomizationID": {},
    "cbc:ProfileID": {},
    "cbc:ID": {},
    "cbc:SalesOrderID": {},
    "cbc:IssueDate": {},
    "cbc:IssueTime": {},
    "cbc:OrderTypeCode": {},
    "cbc:Note": {},
    "cbc:DocumentCurrencyCode": {},
    "cbc:CustomerReference": {},
    "cbc:AccountingCost": {},
    "cac:ValidityPeriod": {"cbc:EndDate": {}},
    "cac:QuotationDocumentReference": {"cbc:ID": {}},
    "cac:OrderDocumentReference": {"cbc:ID": {}},
    "cac:OriginatorDocumentReference": {"cbc:ID": {}},
    "cac:CatalogueReference": {"cbc:ID": {}},
    "cac:AdditionalDocumentReference": {
        "cbc:ID": {},
        "cbc:DocumentType": {},
        "cac:Attachment": {
            "cbc:EmbeddedDocumentBinaryObject": {},
            "cac:ExternalReference": {"cbc:URI": {}},
        },
    },
    "cac:Contract": {"cbc:ID": {}},
    "cac:ProjectReference": {"cbc:ID": {}},
    "cac:BuyerCustomerParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:PartyTaxScheme": {
                "cbc:CompanyID": {},
                "cac:TaxScheme": {"cbc:ID": {}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {},
                "cbc:CompanyID": {},
                "cac:RegistrationAddress": {
                    "cbc:CityName": {},
                    "cac:Country": {"cbc:IdentificationCode": {}},
                },
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:SellerSupplierParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {},
                "cbc:CompanyID": {},
                "cac:RegistrationAddress": {
                    "cbc:CityName": {},
                    "cac:Country": {"cbc:IdentificationCode": {}},
                },
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:OriginatorCustomerParty": {
        "cac:Party": {
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:AccountingCustomerParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:PartyTaxScheme": {
                "cbc:CompanyID": {},
                "cac:TaxScheme": {"cbc:ID": {}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {},
                "cbc:CompanyID": {},
                "cac:RegistrationAddress": {
                    "cbc:CityName": {},
                    "cac:Country": {"cbc:IdentificationCode": {}},
                },
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:Delivery": {
        "cac:DeliveryLocation": {
            "cbc:ID": {},
            "cbc:Name": {},
            "cac:Address": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
        },
        "cac:RequestedDeliveryPeriod": {
            "cbc:StartDate": {},
            "cbc:StartTime": {},
            "cbc:EndDate": {},
            "cbc:EndTime": {},
        },
        "cac:DeliveryParty": {
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        },
        "cac:Despatch": {
            "cbc:RequestedDespatchDate": {},
            "cbc:RequestedDespatchTime": {},
        },
        "cac:Shipment": {
            "cbc:ID": {},
            "cbc:ShippingPriorityLevelCode": {},
            "cac:TransportHandlingUnit": {"cbc:ShippingMarks": {}},
        },
    },
    "cac:DeliveryTerms": {
        "cbc:ID": {},
        "cbc:SpecialTerms": {},
        "cac:DeliveryLocation": {"cbc:ID": {}},
    },
    "cac:PaymentTerms": {"cbc:Note": {}},
    "cac:AllowanceCharge": {
        "cbc:ChargeIndicator": {},
        "cbc:AllowanceChargeReasonCode": {},
        "cbc:AllowanceChargeReason": {},
        "cbc:MultiplierFactorNumeric": {},
        "cbc:Amount": {},
        "cbc:BaseAmount": {},
        "cac:TaxCategory": {
            "cbc:ID": {},
            "cbc:Percent": {},
            "cac:TaxScheme": {"cbc:ID": {}},
        },
    },
    "cac:TaxTotal": {"cbc:TaxAmount": {}},
    "cac:AnticipatedMonetaryTotal": {
        "cbc:LineExtensionAmount": {},
        "cbc:TaxExclusiveAmount": {},
        "cbc:TaxInclusiveAmount": {},
        "cbc:AllowanceTotalAmount": {},
        "cbc:ChargeTotalAmount": {},
        "cbc:PrepaidAmount": {},
        "cbc:PayableRoundingAmount": {},
        "cbc:PayableAmount": {},
    },
    "cac:OrderLine": {
        "cbc:Note": {},
        "cac:LineItem": {
            "cbc:ID": {},
            "cbc:Quantity": {},
            "cbc:LineExtensionAmount": {},
            "cbc:PartialDeliveryIndicator": {},
            "cbc:AccountingCost": {},
            "cac:Delivery": {
                "cbc:ID": {},
                "cac:RequestedDeliveryPeriod": {
                    "cbc:StartDate": {},
                    "cbc:StartTime": {},
                    "cbc:EndDate": {},
                    "cbc:EndTime": {},
                },
            },
            "cac:OriginatorParty": {
                "cac:PartyIdentification": {"cbc:ID": {}},
                "cac:PartyName": {"cbc:Name": {}},
            },
            "cac:AllowanceCharge": {
                "cbc:ChargeIndicator": {},
                "cbc:AllowanceChargeReasonCode": {},
                "cbc:AllowanceChargeReason": {},
                "cbc:MultiplierFactorNumeric": {},
                "cbc:Amount": {},
                "cbc:BaseAmount": {},
            },
            "cac:Price": {
                "cbc:PriceAmount": {},
                "cbc:BaseQuantity": {},
                "cac:AllowanceCharge": {
                    "cbc:ChargeIndicator": {},
                    "cbc:Amount": {},
                    "cbc:BaseAmount": {},
                },
            },
            "cac:Item": {
                "cbc:Description": {},
                "cbc:Name": {},
                "cac:BuyersItemIdentification": {"cbc:ID": {}},
                "cac:SellersItemIdentification": {"cbc:ID": {}},
                "cac:ManufacturersItemIdentification": {"cbc:ID": {}},
                "cac:StandardItemIdentification": {"cbc:ID": {}},
                "cac:ItemSpecificationDocumentReference": {"cbc:ID": {}},
                "cac:CommodityClassification": {"cbc:ItemClassificationCode": {}},
                "cac:ClassifiedTaxCategory": {
                    "cbc:ID": {},
                    "cbc:Percent": {},
                    "cac:TaxScheme": {"cbc:ID": {}},
                },
                "cac:AdditionalItemProperty": {
                    "cbc:ID": {},
                    "cbc:Name": {},
                    "cbc:NameCode": {},
                    "cbc:Value": {},
                    "cbc:ValueQuantity": {},
                    "cbc:ValueQualifier": {},
                },
                "cac:ItemInstance": {
                    "cbc:SerialID": {},
                    "cac:LotIdentification": {"cbc:LotNumberID": {}},
                },
            },
        },
    },
}

OrderChange = {
    "_tag": "OrderChange",
    "cbc:CustomizationID": {},
    "cbc:ProfileID": {},
    "cbc:ID": {},
    "cbc:SalesOrderID": {},
    "cbc:IssueDate": {},
    "cbc:IssueTime": {},
    "cbc:SequenceNumberID": {},
    "cbc:Note": {},
    "cbc:DocumentCurrencyCode": {},
    "cbc:CustomerReference": {},
    "cbc:AccountingCost": {},
    "cac:ValidityPeriod": {"cbc:EndDate": {}},
    "cac:OrderReference": {"cbc:ID": {}},
    "cac:QuotationDocumentReference": {"cbc:ID": {}},
    "cac:OriginatorDocumentReference": {"cbc:ID": {}},
    "cac:AdditionalDocumentReference": {
        "cbc:ID": {},
        "cbc:DocumentType": {},
        "cac:Attachment": {
            "cbc:EmbeddedDocumentBinaryObject": {},
            "cac:ExternalReference": {"cbc:URI": {}},
        },
    },
    "cac:Contract": {"cbc:ID": {}},
    "cac:BuyerCustomerParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:PartyTaxScheme": {
                "cbc:CompanyID": {},
                "cac:TaxScheme": {"cbc:ID": {}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {},
                "cbc:CompanyID": {},
                "cac:RegistrationAddress": {
                    "cbc:CityName": {},
                    "cac:Country": {"cbc:IdentificationCode": {}},
                },
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:SellerSupplierParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {},
                "cbc:CompanyID": {},
                "cac:RegistrationAddress": {
                    "cbc:CityName": {},
                    "cac:Country": {"cbc:IdentificationCode": {}},
                },
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:OriginatorCustomerParty": {
        "cac:Party": {
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:AccountingCustomerParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:PartyTaxScheme": {
                "cbc:CompanyID": {},
                "cac:TaxScheme": {"cbc:ID": {}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {},
                "cbc:CompanyID": {},
                "cac:RegistrationAddress": {
                    "cbc:CityName": {},
                    "cac:Country": {"cbc:IdentificationCode": {}},
                },
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:Delivery": {
        "cac:DeliveryLocation": {
            "cbc:ID": {},
            "cbc:Name": {},
            "cac:Address": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
        },
        "cac:RequestedDeliveryPeriod": {
            "cbc:StartDate": {},
            "cbc:StartTime": {},
            "cbc:EndDate": {},
            "cbc:EndTime": {},
        },
        "cac:DeliveryParty": {
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        },
        "cac:Shipment": {
            "cbc:ID": {},
            "cac:TransportHandlingUnit": {"cbc:ShippingMarks": {}},
        },
    },
    "cac:DeliveryTerms": {
        "cbc:ID": {},
        "cbc:SpecialTerms": {},
        "cac:DeliveryLocation": {"cbc:ID": {}},
    },
    "cac:PaymentTerms": {"cbc:Note": {}},
    "cac:AllowanceCharge": {
        "cbc:ChargeIndicator": {},
        "cbc:AllowanceChargeReasonCode": {},
        "cbc:AllowanceChargeReason": {},
        "cbc:MultiplierFactorNumeric": {},
        "cbc:Amount": {},
        "cbc:BaseAmount": {},
        "cac:TaxCategory": {
            "cbc:ID": {},
            "cbc:Percent": {},
            "cac:TaxScheme": {"cbc:ID": {}},
        },
    },
    "cac:TaxTotal": {"cbc:TaxAmount": {}},
    "cac:AnticipatedMonetaryTotal": {
        "cbc:LineExtensionAmount": {},
        "cbc:TaxExclusiveAmount": {},
        "cbc:TaxInclusiveAmount": {},
        "cbc:AllowanceTotalAmount": {},
        "cbc:ChargeTotalAmount": {},
        "cbc:PrepaidAmount": {},
        "cbc:PayableRoundingAmount": {},
        "cbc:PayableAmount": {},
    },
    "cac:OrderLine": {
        "cbc:Note": {},
        "cac:LineItem": {
            "cbc:ID": {},
            "cbc:LineStatusCode": {},
            "cbc:Quantity": {},
            "cbc:LineExtensionAmount": {},
            "cbc:PartialDeliveryIndicator": {},
            "cbc:AccountingCost": {},
            "cac:Delivery": {
                "cbc:ID": {},
                "cac:RequestedDeliveryPeriod": {
                    "cbc:StartDate": {},
                    "cbc:StartTime": {},
                    "cbc:EndDate": {},
                    "cbc:EndTime": {},
                },
            },
            "cac:OriginatorParty": {
                "cac:PartyIdentification": {"cbc:ID": {}},
                "cac:PartyName": {"cbc:Name": {}},
            },
            "cac:AllowanceCharge": {
                "cbc:ChargeIndicator": {},
                "cbc:AllowanceChargeReasonCode": {},
                "cbc:AllowanceChargeReason": {},
                "cbc:MultiplierFactorNumeric": {},
                "cbc:Amount": {},
                "cbc:BaseAmount": {},
            },
            "cac:Price": {
                "cbc:PriceAmount": {},
                "cbc:BaseQuantity": {},
                "cac:AllowanceCharge": {
                    "cbc:ChargeIndicator": {},
                    "cbc:Amount": {},
                    "cbc:BaseAmount": {},
                },
            },
            "cac:Item": {
                "cbc:Description": {},
                "cbc:Name": {},
                "cac:BuyersItemIdentification": {"cbc:ID": {}},
                "cac:SellersItemIdentification": {"cbc:ID": {}},
                "cac:StandardItemIdentification": {"cbc:ID": {}},
                "cac:ItemSpecificationDocumentReference": {"cbc:ID": {}},
                "cac:CommodityClassification": {"cbc:ItemClassificationCode": {}},
                "cac:ClassifiedTaxCategory": {
                    "cbc:ID": {},
                    "cbc:Percent": {},
                    "cac:TaxScheme": {"cbc:ID": {}},
                },
                "cac:AdditionalItemProperty": {
                    "cbc:ID": {},
                    "cbc:Name": {},
                    "cbc:NameCode": {},
                    "cbc:Value": {},
                    "cbc:ValueQuantity": {},
                    "cbc:ValueQualifier": {},
                },
                "cac:ItemInstance": {
                    "cbc:SerialID": {},
                    "cac:LotIdentification": {"cbc:LotNumberID": {}},
                },
            },
        },
    },
}

OrderCancel = {
    "_tag": "OrderCancellation",
    "cbc:CustomizationID": {},
    "cbc:ProfileID": {},
    "cbc:ID": {},
    "cbc:IssueDate": {},
    "cbc:IssueTime": {},
    "cbc:Note": {},
    "cbc:CancellationNote": {},
    "cac:OrderReference": {"cbc:ID": {}},
    "cac:OriginatorDocumentReference": {"cbc:ID": {}},
    "cac:AdditionalDocumentReference": {
        "cbc:ID": {},
        "cbc:DocumentType": {},
        "cac:Attachment": {
            "cbc:EmbeddedDocumentBinaryObject": {},
            "cac:ExternalReference": {"cbc:URI": {}},
        },
    },
    "cac:Contract": {"cbc:ID": {}},
    "cac:BuyerCustomerParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:PartyTaxScheme": {
                "cbc:CompanyID": {},
                "cac:TaxScheme": {"cbc:ID": {}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {},
                "cbc:CompanyID": {},
                "cac:RegistrationAddress": {
                    "cbc:CityName": {},
                    "cac:Country": {"cbc:IdentificationCode": {}},
                },
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:SellerSupplierParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:PostalAddress": {
                "cbc:StreetName": {},
                "cbc:AdditionalStreetName": {},
                "cbc:CityName": {},
                "cbc:PostalZone": {},
                "cbc:CountrySubentity": {},
                "cac:AddressLine": {"cbc:Line": {}},
                "cac:Country": {"cbc:IdentificationCode": {}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {},
                "cbc:CompanyID": {},
                "cac:RegistrationAddress": {
                    "cbc:CityName": {},
                    "cac:Country": {"cbc:IdentificationCode": {}},
                },
            },
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:OriginatorCustomerParty": {
        "cac:Party": {
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyName": {"cbc:Name": {}},
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
}

OrderBalance = {
    "_tag": "Order",
    "cbc:CustomizationID": {},
    "cbc:ProfileID": {},
    "cbc:ID": {},
    "cbc:IssueDate": {},
    "cbc:IssueTime": {},
    "cbc:OrderTypeCode": {},
    "cbc:Note": {},
    "cbc:DocumentCurrencyCode": {},
    "cbc:CustomerReference": {},
    "cac:OrderDocumentReference": {"cbc:ID": {}, "cbc:IssueDate": {}},
    "cac:BuyerCustomerParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyLegalEntity": {"cbc:RegistrationName": {}, "cbc:CompanyID": {}},
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:SellerSupplierParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyLegalEntity": {"cbc:RegistrationName": {}, "cbc:CompanyID": {}},
            "cac:Contact": {
                "cbc:Name": {},
                "cbc:Telephone": {},
                "cbc:ElectronicMail": {},
            },
        }
    },
    "cac:PaymentTerms": {"cbc:Note": {}},
    "cac:AnticipatedMonetaryTotal": {
        "cbc:LineExtensionAmount": {},
        "cbc:PayableAmount": {},
    },
    "cac:OrderLine": {
        "cbc:Note": {},
        "cac:LineItem": {
            "cbc:ID": {},
            "cbc:Quantity": {},
            "cbc:LineExtensionAmount": {},
            "cac:Price": {"cbc:PriceAmount": {}},
            "cac:Item": {"cbc:Name": {}},
        },
    },
}
