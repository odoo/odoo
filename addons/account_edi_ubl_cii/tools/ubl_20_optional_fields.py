PEPPOL_COMMON_OPTIONAL_FIELDS = {
    "x_studio_peppol_tax_point_date": {
        "path": ["cbc:TaxPointDate"],
        "attrs": lambda invoice: {
            "_text": invoice.x_studio_peppol_tax_point_date,
        },
        'supported_types': ['date'],
    },
    "x_studio_peppol_contract_document_reference_id": {
        "path": ["cac:ContractDocumentReference", "cbc:ID"],
        "attrs": lambda invoice: {
            '_text': invoice.x_studio_peppol_contract_document_reference_id,
        },
        'supported_types': ['char', 'text'],
    },
    "x_studio_peppol_despatch_document_reference_id": {
        "path": ["cac:DespatchDocumentReference", "cbc:ID"],
        "attrs": lambda invoice: {
            '_text': invoice.x_studio_peppol_despatch_document_reference_id,
        },
        'supported_types': ['char', 'text'],
    },
    "x_studio_peppol_accounting_cost": {
        "path": ["cbc:AccountingCost"],
        "attrs": lambda invoice: {
            '_text': invoice.x_studio_peppol_accounting_cost,
        },
        'supported_types': ['char', 'text'],
    },
    "x_studio_peppol_order_reference_id": {
        "path": ["cac:OrderReference", "cbc:ID"],
        "attrs": lambda invoice: {
            '_text': invoice.x_studio_peppol_order_reference_id,
        },
        'supported_types': ['char', 'text'],
    },
    "x_studio_peppol_invoice_period_start_date": {
        "path": ["cac:InvoicePeriod", "cbc:StartDate"],
        "attrs": lambda invoice: {
            '_text': invoice.x_studio_peppol_invoice_period_start_date,
        },
        'supported_types': ['date'],
    },
    "x_studio_peppol_invoice_period_end_date": {
        "path": ["cac:InvoicePeriod", "cbc:EndDate"],
        "attrs": lambda invoice: {
            '_text': invoice.x_studio_peppol_invoice_period_end_date,
        },
        'supported_types': ['date'],
    },
}

PEPPOL_INVOICE_OPTIONAL_FIELDS = {
    **PEPPOL_COMMON_OPTIONAL_FIELDS,
    "x_studio_peppol_project_reference_id": {
        "path": ["cac:ProjectReference", "cbc:ID"],
        "attrs": lambda invoice: {
            '_text': invoice.x_studio_peppol_project_reference_id,
        },
        'supported_types': ['char', 'text'],
    },
}

PEPPOL_CREDIT_NOTE_OPTIONAL_FIELDS = {
    **PEPPOL_COMMON_OPTIONAL_FIELDS,
}

PEPPOL_COMMON_OPTIONAL_LINE_FIELDS = {
    "x_studio_peppol_order_line_reference_id": {
        "path": ["cac:OrderLineReference", "cbc:LineID"],
        "attrs": lambda line: {
            '_text': line.x_studio_peppol_order_line_reference_id,
        },
        'supported_types': ['char', 'text'],
    },
    "x_studio_peppol_buyers_item_id": {
        "path": ["cac:Item", "cac:BuyersItemIdentification", "cbc:ID"],
        "attrs": lambda line: {
            '_text': line.x_studio_peppol_buyers_item_id,
        },
        'supported_types': ['char', 'text'],
    },
}

PEPPOL_INVOICE_OPTIONAL_LINE_FIELDS = {
    **PEPPOL_COMMON_OPTIONAL_LINE_FIELDS,
}

PEPPOL_CREDIT_NOTE_OPTIONAL_LINE_FIELDS = {
    **PEPPOL_COMMON_OPTIONAL_LINE_FIELDS,
}
