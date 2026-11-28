OrderResponse = {
    "_tag": "OrderResponse",
    "cbc:CustomizationID": {},
    "cbc:ProfileID": {},
    "cbc:ID": {},
    "cbc:SalesOrderID": {},
    "cbc:IssueDate": {},
    "cbc:IssueTime": {},
    "cbc:OrderResponseCode": {},
    "cbc:Note": {},
    "cbc:DocumentCurrencyCode": {},
    "cbc:CustomerReference": {},
    "cac:OrderReference": {"cbc:ID": {}},
    "cac:OrderChangeDocumentReference": {"cbc:ID": {}},
    "cac:SellerSupplierParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyLegalEntity": {"cbc:RegistrationName": {}},
        }
    },
    "cac:BuyerCustomerParty": {
        "cac:Party": {
            "cbc:EndpointID": {},
            "cac:PartyIdentification": {"cbc:ID": {}},
            "cac:PartyLegalEntity": {"cbc:RegistrationName": {}},
        }
    },
    "cac:Delivery": {
        "cac:PromisedDeliveryPeriod": {
            "cbc:StartDate": {},
            "cbc:StartTime": {},
            "cbc:EndDate": {},
            "cbc:EndTime": {},
        }
    },
    "cac:OrderLine": {
        "cac:LineItem": {
            "cbc:ID": {},
            "cbc:Note": {},
            "cbc:LineStatusCode": {},
            "cbc:Quantity": {},
            "cbc:MaximumBackorderQuantity": {},
            "cac:Delivery": {
                "cac:PromisedDeliveryPeriod": {
                    "cbc:StartDate": {},
                    "cbc:StartTime": {},
                    "cbc:EndDate": {},
                    "cbc:EndTime": {},
                }
            },
            "cac:Price": {"cbc:PriceAmount": {}, "cbc:BaseQuantity": {}},
            "cac:Item": {
                "cbc:Name": {},
                "cac:BuyersItemIdentification": {"cbc:ID": {}},
                "cac:SellersItemIdentification": {"cbc:ID": {}},
                "cac:StandardItemIdentification": {"cbc:ID": {}},
            },
        },
        "cac:SellerSubstitutedLineItem": {
            "cbc:ID": {},
            "cac:Item": {
                "cbc:Name": {},
                "cac:SellersItemIdentification": {"cbc:ID": {}},
                "cac:StandardItemIdentification": {"cbc:ID": {}},
                "cac:CommodityClassification": {"cbc:ItemClassificationCode": {}},
                "cac:ClassifiedTaxCategory": {
                    "cbc:ID": {},
                    "cbc:Percent": {},
                    "cac:TaxScheme": {"cbc:ID": {}},
                },
                "cac:AdditionalItemProperty": {
                    "cbc:Name": {},
                    "cbc:NameCode": {},
                    "cbc:Value": {},
                    "cbc:ValueQuantity": {},
                    "cbc:ValueQualifier": {},
                },
            },
        },
        "cac:OrderLineReference": {"cbc:LineID": {}},
    },
}
