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


# GİB invoice type -> the `code_type` values of the reasons it may use.
EXEMPTION_CODE_TYPES = {
    'ISTISNA': {'exception', 'export_exception'},
    'IHRACKAYITLI': {'export_registration'},
    'TEVKIFAT': {'withholding'},
    'TEVKIFATIADE': {'withholding'},
}
