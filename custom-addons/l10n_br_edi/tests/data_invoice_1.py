# Part of Odoo. See LICENSE file for full copyright and licensing details.
invoice_1_request = {
    "header": {
        "amountCalcType": "gross",
        "companyLocation": "49233848000150",
        "documentCode": "account.move_44",
        "goods": {"class": "TEST CLASS VALUE", "tplmp": "4"},
        "invoiceNumber": "00000009",
        "invoiceSerial": "1",
        "locations": {
            "entity": {
                "activitySector": {"code": "industry"},
                "address": {
                    "cityName": "Rio de Janeiro",
                    "email": "x@example.com",
                    "neighborhood": "Centros",
                    "number": "592",
                    "state": "Rio de Janeiro",
                    "street": "Av. Presidente Vargas",
                    "zipcode": "20071-001",
                },
                "businessName": "BR Company Customer",
                "federalTaxId": "51494569013170",
                "taxRegime": "simplified",
                "taxesSettings": {"icmsTaxPayer": True},
                "type": "individual",
            },
            "establishment": {
                "activitySector": {"code": "service"},
                "address": {"cityName": "Curitaba", "countryCode": "1058", "state": "Paraná", "zipcode": "80010-010"},
                "businessName": "BR Company",
                "federalTaxId": "49233848000150",
                "stateTaxId": "9102799558",
                "taxRegime": "estimatedProfit",
                "taxesSettings": {"icmsTaxPayer": True},
                "type": "business",
            },
        },
        "messageType": "goods",
        "paymentInfo": {"paymentMode": [{"cardTpIntegration": "1", "mode": False}]},
        "transactionDate": "2023-10-04",
    },
    "lines": [
        {
            "cfop": 6101,
            "freightAmount": 0,
            "goods": {"entityIcmsStSubstitute": "default", "subjectToIPIonInbound": True},
            "insuranceAmount": 0,
            "itemCode": "FURN_6666",
            "itemDescriptor": {
                "cest": "",
                "description": "Acoustic Bloc Screens",
                "hsCode": "49011000",
                "productType": "FOR PRODUCT",
                "source": "0",
            },
            "lineAdditionalInfo": "",
            "lineAmount": 295,
            "lineCode": 146,
            "lineNetFigure": 259.6,
            "lineTaxedDiscount": 0,
            "lineUnitPrice": 295,
            "numberOfItems": 1,
            "operationType": "standardSales",
            "otherCostAmount": 0,
            "overwrite": "no",
            "taxDetails": [
                {
                    "citation": "Trib aprox R$ 39,68 Federal e R$ 56,05 Estadual Fonte: IBPT",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "rate": 13.45,
                    "subtotalTaxable": 295,
                    "tax": 39.68,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Informative",
                        "impactOnNetAmount": "Informative",
                    },
                    "taxType": "aproxtribFed",
                },
                {
                    "exemptionCode": "",
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "rate": 19,
                    "subtotalTaxable": 295,
                    "tax": 56.05,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Informative",
                        "impactOnNetAmount": "Informative",
                    },
                    "taxType": "aproxtribState",
                },
                {
                    "calcMode": "rate",
                    "citation": "PIS/COFINS com alíquota zero "
                    'conforme: "Lei nº 10.865/2004, Artigo '
                    "28, Inciso VI, incluído pela Lei nº "
                    '11.033/2004"',
                    "citationId": "1f0f4a6e-4e31-41b5-9d6a-14f36bf00b34",
                    "cst": "06",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "rate": 0,
                    "subtotalTaxable": 295,
                    "tax": 0,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Included",
                        "impactOnNetAmount": "Included",
                    },
                    "taxType": "cofins",
                },
                {
                    "citation": "ICMS/PR_Decreto nº 7.871/2017, Artigo 18, Inciso I",
                    "citationId": "b4655cef-0f17-4c21-a94c-760d8e965b72",
                    "cst": "00",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Paraná",
                    "jurisdictionType": "State",
                    "modBC": "3",
                    "rate": 12,
                    "source": "0",
                    "subtotalTaxable": 295,
                    "tax": 35.4,
                    "taxImpact": {
                        "accounting": "liability",
                        "impactOnFinalPrice": "Included",
                        "impactOnNetAmount": "Included",
                    },
                    "taxType": "icms",
                },
                {
                    "calcMode": "rate",
                    "citation": 'IPI não tributado conforme: "Decreto '
                    "nº 11.158/22, Artigo 1º, Anexos I, "
                    'II, III, IV"',
                    "citationId": "743f28a0-119c-11ed-893f-d18780a30701",
                    "cst": "53",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "legalTaxClass": 999,
                    "rate": 0,
                    "subtotalTaxable": 295,
                    "tax": 0,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Informative",
                        "impactOnNetAmount": "Informative",
                    },
                    "taxType": "ipi",
                    "traceCode": "C005",
                },
                {
                    "calcMode": "rate",
                    "citation": "PIS/COFINS com alíquota zero "
                    'conforme: "Lei nº 10.865/2004, Artigo '
                    "28, Inciso VI, incluído pela Lei nº "
                    '11.033/2004"',
                    "citationId": "85119944-8343-471d-b952-d49f77cb4277",
                    "cst": "06",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "rate": 0,
                    "subtotalTaxable": 295,
                    "tax": 0,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Included",
                        "impactOnNetAmount": "Included",
                    },
                    "taxType": "pis",
                },
            ],
            "useType": "use or consumption",
            "warnings": [
                {
                    "citation": "Subject to PIS Benefits: "
                    '"PIS_Constituição Federal de 1988, '
                    'Artigo 150, Inciso VI, Alínea d"',
                    "code": "WC003",
                    "description": "Sem prejuízo de outras garantias "
                    "asseguradas ao contribuinte, é "
                    "vedado à União, aos Estados, ao "
                    "Distrito Federal e aos Municípios "
                    "instituir impostos sobre livros, "
                    "jornais, periódicos e o papel "
                    "destinado a sua impressão",
                    "id": "83714234-6adb-4997-84be-2cc8f9ec5e87",
                    "isCustomCitation": False,
                },
                {
                    "citation": "Subject to COFINS Benefits: "
                    '"COFINS_Constituição Federal de 1988, '
                    'Artigo 150, Inciso VI, Alínea d"',
                    "code": "WC003",
                    "description": "Sem prejuízo de outras garantias "
                    "asseguradas ao contribuinte, é "
                    "vedado à União, aos Estados, ao "
                    "Distrito Federal e aos Municípios "
                    "instituir impostos sobre livros, "
                    "jornais, periódicos e o papel "
                    "destinado a sua impressão",
                    "id": "c0291665-0cfe-4dfc-9795-f85bf67ea9d3",
                    "isCustomCitation": False,
                },
                {
                    "citation": 'Subject to ICMS Benefits: "ICMS/PR_Decreto nº 7.871/2017, Artigo 3º, Inciso I"',
                    "code": "WC001",
                    "description": "O imposto não incide sobre_operações com",
                    "id": "2812bec2-1a84-453e-b59e-869395b2f05e",
                    "isCustomCitation": False,
                },
                {
                    "citation": 'Subject to ICMS Benefits: "ICMS/PR_Decreto nº 7.871/2017, Artigo 3º, Inciso I"',
                    "code": "WC001",
                    "description": "O imposto não incide sobre_operações com",
                    "id": "325e1ed4-e9bd-4983-be4f-37fdb23e4fde",
                    "isCustomCitation": False,
                },
                {
                    "citation": "Subject to ICMS_Deferral Benefits: "
                    '"ICMS/PR_Decreto nº 7.871/2017, Anexo '
                    "VIII, Artigo 28, Inciso I, Alínea "
                    'a_Alíquota 19%"',
                    "code": "WC002",
                    "description": "Verificar as regras de aplicação e "
                    "cessação do diferimento determinadas "
                    "pelo Anexo VIII, Artigo 28 do "
                    "RICMS/PR",
                    "id": "c0b0d7f0-bf99-11ed-a6fa-01c00aa3ee75",
                    "isCustomCitation": False,
                },
                {
                    "citation": "Subject to ICMS_Inter Benefits: "
                    '"ICMS/PR_Decreto nº 7.871/2017, Artigo '
                    '3º, Inciso I"',
                    "code": "WC001",
                    "description": "O imposto não incide sobre_operações com",
                    "id": "2cc6c36b-e713-4d18-86c8-2eec66bd1720",
                    "isCustomCitation": False,
                },
                {
                    "citation": "Subject to ICMS_Inter Benefits: "
                    '"ICMS/PR_Decreto nº 7.871/2017, Artigo '
                    '3º, Inciso I"',
                    "code": "WC001",
                    "description": "O imposto não incide sobre_operações com",
                    "id": "a2021c59-33f3-4ff4-8bf0-5be216048c02",
                    "isCustomCitation": False,
                },
            ],
        },
        {
            "cfop": 6101,
            "freightAmount": 0,
            "goods": {"entityIcmsStSubstitute": "default", "subjectToIPIonInbound": True},
            "insuranceAmount": 0,
            "itemCode": "E-COM11",
            "itemDescriptor": {
                "cest": "",
                "description": "Cabinet with Doors",
                "hsCode": "49011000",
                "productType": "FOR PRODUCT",
                "source": "0",
            },
            "lineAdditionalInfo": "",
            "lineAmount": 140,
            "lineCode": 154,
            "lineNetFigure": 123.2,
            "lineTaxedDiscount": 0,
            "lineUnitPrice": 140,
            "numberOfItems": 1,
            "operationType": "standardSales",
            "otherCostAmount": 0,
            "overwrite": "no",
            "taxDetails": [
                {
                    "citation": "Trib aprox R$ 18,83 Federal e R$ 26,60 Estadual Fonte: IBPT",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "rate": 13.45,
                    "subtotalTaxable": 140,
                    "tax": 18.83,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Informative",
                        "impactOnNetAmount": "Informative",
                    },
                    "taxType": "aproxtribFed",
                },
                {
                    "exemptionCode": "",
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "rate": 19,
                    "ruleId": None,
                    "ruleCode": None,
                    "subtotalTaxable": 140,
                    "tax": 26.6,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Informative",
                        "impactOnNetAmount": "Informative",
                    },
                    "taxType": "aproxtribState",
                },
                {
                    "calcMode": "rate",
                    "citation": "PIS/COFINS com alíquota zero "
                    'conforme: "Lei nº 10.865/2004, Artigo '
                    "28, Inciso VI, incluído pela Lei nº "
                    '11.033/2004"',
                    "citationId": "1f0f4a6e-4e31-41b5-9d6a-14f36bf00b34",
                    "cst": "06",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "rate": 0,
                    "subtotalTaxable": 140,
                    "tax": 0,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Included",
                        "impactOnNetAmount": "Included",
                    },
                    "taxType": "cofins",
                },
                {
                    "citation": "ICMS/PR_Decreto nº 7.871/2017, Artigo 18, Inciso I",
                    "citationId": "b4655cef-0f17-4c21-a94c-760d8e965b72",
                    "cst": "00",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Paraná",
                    "jurisdictionType": "State",
                    "modBC": "3",
                    "rate": 12,
                    "source": "0",
                    "subtotalTaxable": 140,
                    "tax": 16.8,
                    "taxImpact": {
                        "accounting": "liability",
                        "impactOnFinalPrice": "Included",
                        "impactOnNetAmount": "Included",
                    },
                    "taxType": "icms",
                },
                {
                    "calcMode": "rate",
                    "citation": 'IPI não tributado conforme: "Decreto '
                    "nº 11.158/22, Artigo 1º, Anexos I, "
                    'II, III, IV"',
                    "citationId": "743f28a0-119c-11ed-893f-d18780a30701",
                    "cst": "53",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "legalTaxClass": 999,
                    "rate": 0,
                    "subtotalTaxable": 140,
                    "tax": 0,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Informative",
                        "impactOnNetAmount": "Informative",
                    },
                    "taxType": "ipi",
                    "traceCode": "C005",
                },
                {
                    "calcMode": "rate",
                    "citation": "PIS/COFINS com alíquota zero "
                    'conforme: "Lei nº 10.865/2004, Artigo '
                    "28, Inciso VI, incluído pela Lei nº "
                    '11.033/2004"',
                    "citationId": "85119944-8343-471d-b952-d49f77cb4277",
                    "cst": "06",
                    "exemptionCode": "",
                    "isCustomCitation": False,
                    "jurisdictionName": "Brazil",
                    "jurisdictionType": "Country",
                    "rate": 0,
                    "subtotalTaxable": 140,
                    "tax": 0,
                    "taxImpact": {
                        "accounting": "none",
                        "impactOnFinalPrice": "Included",
                        "impactOnNetAmount": "Included",
                    },
                    "taxType": "pis",
                },
            ],
            "useType": "use or consumption",
            "warnings": [
                {
                    "citation": "Subject to PIS Benefits: "
                    '"PIS_Constituição Federal de 1988, '
                    'Artigo 150, Inciso VI, Alínea d"',
                    "code": "WC003",
                    "description": "Sem prejuízo de outras garantias "
                    "asseguradas ao contribuinte, é "
                    "vedado à União, aos Estados, ao "
                    "Distrito Federal e aos Municípios "
                    "instituir impostos sobre livros, "
                    "jornais, periódicos e o papel "
                    "destinado a sua impressão",
                    "id": "83714234-6adb-4997-84be-2cc8f9ec5e87",
                    "isCustomCitation": False,
                },
                {
                    "citation": "Subject to COFINS Benefits: "
                    '"COFINS_Constituição Federal de 1988, '
                    'Artigo 150, Inciso VI, Alínea d"',
                    "code": "WC003",
                    "description": "Sem prejuízo de outras garantias "
                    "asseguradas ao contribuinte, é "
                    "vedado à União, aos Estados, ao "
                    "Distrito Federal e aos Municípios "
                    "instituir impostos sobre livros, "
                    "jornais, periódicos e o papel "
                    "destinado a sua impressão",
                    "id": "c0291665-0cfe-4dfc-9795-f85bf67ea9d3",
                    "isCustomCitation": False,
                },
                {
                    "citation": 'Subject to ICMS Benefits: "ICMS/PR_Decreto nº 7.871/2017, Artigo 3º, Inciso I"',
                    "code": "WC001",
                    "description": "O imposto não incide sobre_operações com",
                    "id": "2812bec2-1a84-453e-b59e-869395b2f05e",
                    "isCustomCitation": False,
                },
                {
                    "citation": 'Subject to ICMS Benefits: "ICMS/PR_Decreto nº 7.871/2017, Artigo 3º, Inciso I"',
                    "code": "WC001",
                    "description": "O imposto não incide sobre_operações com",
                    "id": "325e1ed4-e9bd-4983-be4f-37fdb23e4fde",
                    "isCustomCitation": False,
                },
                {
                    "citation": "Subject to ICMS_Deferral Benefits: "
                    '"ICMS/PR_Decreto nº 7.871/2017, Anexo '
                    "VIII, Artigo 28, Inciso I, Alínea "
                    'a_Alíquota 19%"',
                    "code": "WC002",
                    "description": "Verificar as regras de aplicação e "
                    "cessação do diferimento determinadas "
                    "pelo Anexo VIII, Artigo 28 do "
                    "RICMS/PR",
                    "id": "c0b0d7f0-bf99-11ed-a6fa-01c00aa3ee75",
                    "isCustomCitation": False,
                },
                {
                    "citation": "Subject to ICMS_Inter Benefits: "
                    '"ICMS/PR_Decreto nº 7.871/2017, Artigo '
                    '3º, Inciso I"',
                    "code": "WC001",
                    "description": "O imposto não incide sobre_operações com",
                    "id": "2cc6c36b-e713-4d18-86c8-2eec66bd1720",
                    "isCustomCitation": False,
                },
                {
                    "citation": "Subject to ICMS_Inter Benefits: "
                    '"ICMS/PR_Decreto nº 7.871/2017, Artigo '
                    '3º, Inciso I"',
                    "code": "WC001",
                    "description": "O imposto não incide sobre_operações com",
                    "id": "a2021c59-33f3-4ff4-8bf0-5be216048c02",
                    "isCustomCitation": False,
                },
            ],
        },
    ],
    "summary": {
        "numberOfLines": 2,
        "taxByType": {
            "aproxtribFed": {
                "jurisdictions": [{"jurisdictionName": "Brazil", "jurisdictionType": "Country", "tax": 58.51}],
                "subtotalTaxable": 435,
                "tax": 58.51,
            },
            "aproxtribState": {
                "jurisdictions": [{"jurisdictionName": "Brazil", "jurisdictionType": "Country", "tax": 82.65}],
                "subtotalTaxable": 435,
                "tax": 82.65,
            },
            "cofins": {
                "jurisdictions": [{"jurisdictionName": "Brazil", "jurisdictionType": "Country", "tax": 0}],
                "subtotalTaxable": 435,
            },
            "icms": {
                "jurisdictions": [{"jurisdictionName": "Paraná", "jurisdictionType": "State", "tax": 52.2}],
                "subtotalTaxable": 435,
                "tax": 52.2,
            },
            "ipi": {
                "jurisdictions": [{"jurisdictionName": "Brazil", "jurisdictionType": "Country", "tax": 0}],
                "subtotalTaxable": 435,
            },
            "pis": {
                "jurisdictions": [{"jurisdictionName": "Brazil", "jurisdictionType": "Country", "tax": 0}],
                "subtotalTaxable": 435,
            },
        },
        "taxImpactHighlights": {
            "included": [
                {"subtotalTaxable": 435, "tax": 0, "taxType": "cofins"},
                {"subtotalTaxable": 435, "tax": 52.2, "taxType": "icms"},
                {"subtotalTaxable": 435, "tax": 0, "taxType": "pis"},
            ],
            "informative": [
                {"subtotalTaxable": 435, "tax": 58.51, "taxType": "aproxtribFed"},
                {"subtotalTaxable": 435, "tax": 82.65, "taxType": "aproxtribState"},
                {"subtotalTaxable": 435, "tax": 0, "taxType": "ipi"},
            ],
        },
        "totalInvoice": 435,
        "totalLineAmounts": 435,
    },
}

invoice_1_submit_success_response = {
    "key": "XXX",
    "pdf": {
        "base64": "eW9sbwo=",
        "link": "https://homolog.invoicy.com.br///DownloadPDF.aspx?XXX",
    },
    "protocol": "141230000764325",
    "state": "PR",
    "status": {
        "accessKey": "XXX",
        "authorizationDateTime": "2023-10-05T14:27:03-03:00",
        "code": "100",
        "desc": "Autorizado o uso da NF-e",
        "number": "9",
        "protocol": "141230000764325",
        "serial": "1",
    },
    "subscriptionId": "XXX",
    "xml": {
        "base64": "eW9sbwo="
    },
}

invoice_1_submit_fail_response = {
    "error": {
        "code": "225",
        "message": "Seu documento foi rejeitado pela SEFAZ pelo seguinte "
        "motivo:\n"
        "Falha nos dados do campo "
        "Envio/dest/enderDest/xBairro_dest/. O Bairro do "
        "destinatário possui um valor inválido. - Valor "
        'informado: ""\n'
        "Revise as informação do campo no documento e envie "
        "novamente para autorização.",
    }
}

invoice_1_cancel_success_response = {
  "status": {
    "code": "101",
    "desc": "Cancelamento de NF-e homologado",
    "protocol": "141230000867793",
    "authorizationDateTime": "2023-11-21T15:14:24-03:00"
  },
  "xml": {
    "base64": "eW9sbwo=",
    "link": "https://homolog.invoicy.com.br///HNUC002.aspx?ParmCript=XXX&DocDetArqCodigo=0&DocEveTipo=0&DocEvenSeq=0"
  },
  "pdf": {
    "base64": None,
    "link": None
  }
}

invoice_1_correct_success_response = {
  "key": "XXX",
  "subscriptionId": "XXX",
  "status": {
    "code": "135",
    "desc": "Evento registrado e vinculado a NF-e",
    "protocol": "141230000867790",
    "accessKey": "XXX",
    "authorizationDateTime": "2023-11-21T15:14:00-03:00"
  },
  "xml": {
    "base64": "eW9sbwo=",
    "link": "https://homolog.invoicy.com.br///HNUC002.aspx?ParmCript=XXX&DocDetArqCodigo=0&DocEveTipo=0&DocEvenSeq=0"
  },
  "pdf": {
    "base64": "eW9sbwo=",
    "link": "https://homolog.invoicy.com.br///DownloadPDFEvento.aspx?XXX"
  }
}

invoice_1_correct_fail_response = {
  "key": "XXX",
  "subscriptionId": "XXX",
  "status": {
    "code": "493",
    "desc": "Evento nao atende o Schema XML especifico. org.xml.sax.SAXParseException; lineNumber: 1; columnNumber: 138; cvc-minLength-valid: Value apos;aapos; with length = apos;1apos; is not facet-valid with respect to minLength apos;15apos; for type apos;#AnonType_xCorrecaodetEventoCCeapos;.",
    "protocol": None,
    "accessKey": "XXX",
    "authorizationDateTime": {}
  },
  "xml": {
    "base64": None,
    "link": None
  },
  "pdf": {
    "base64": None,
    "link": None
  }
}
