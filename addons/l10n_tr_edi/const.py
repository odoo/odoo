# Generic numbers accepted by the GİB in place of a real VKN or TCKN
L10N_TR_GIB_ALLOWED_NUMS = {'11111111111', '2222222222'}

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

# l10n_tr_edi.document state of the e-Invoice / e-Archive -> account.move send status
DOCUMENT_STATE_TO_SEND_STATUS = {
    'draft': 'draft_sent',
    'sent': 'sent',
    'waiting': 'waiting',
    'accepted': 'succeed',
    'error': 'error',
    'cancelled': 'cancelled',
}

# Answer to a received commercial bill -> state of its commercial response document
COMMERCIAL_ANSWER_TO_DOCUMENT_STATE = {
    'approved': 'accepted',
    'rejected': 'rejected',
}

# l10n_tr_edi.document state of the commercial response -> account.move send status
COMMERCIAL_RESPONSE_STATE_TO_SEND_STATUS = {
    'accepted': 'commercial_approved',
    'accepted_automatically': 'commercial_answered_automatically',
    'rejected': 'commercial_rejected',
}
