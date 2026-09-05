MOVE_TYPE_CATEGORY_MAP = {
    "out_invoice": {
        "earchive": "invoices",
        "einvoice": "sale",
    },
    "in_invoice": {
        "einvoice": "purchase",
    },
}

CATEGORY_MOVE_TYPE_MAP = {
    "invoices": "out_invoice",
    "sale": "out_invoice",
    "purchase": "in_invoice",
}

TICARIFATURA_ANSWER_TO_FIELD_VALUE_MAP = {
    "approved": "commercial_approved",
    "rejected": "commercial_rejected",
    "documentAnsweredAutomatically": "commercial_answered_automatically",
}

GIB_INVOICE_SCENARIO_SELECTION = [
    ('TEMELFATURA', "Basic"),
    ('KAMU', "Public Sector"),
    ('TICARIFATURA', "Commercial"),
]

GIB_INVOICE_TYPE_SELECTION = [
    ('SATIS', "Sales"),
    ('TEVKIFAT', "Withholding"),
    ('IHRACKAYITLI', "Registered for Export"),
    ('ISTISNA', "Tax Exempt"),
    ('IADE', "Return"),
    ('TEVKIFATIADE', "Withholding Return"),
]

GIB_RETURN_INVOICE_TYPES = ('IADE', 'TEVKIFATIADE')

SUCCESSFUL_SEND_STATUSES = {'succeed', 'commercial_approved', 'commercial_answered_automatically'}
