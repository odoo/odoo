PT_CERTIFICATION_NUMBER = "9999"  # TODO: Fill with Certificate number provided by the Tax Authority

# Simplified invoice (FS) limits per Portuguese VAT code:
# goods <= 1000 EUR, services <= 100 EUR
PT_SIMPLIFIED_INVOICE_GOODS_LIMIT = 1000.0
PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT = 100.0

# Mapping from Odoo document_type to AT webservice classeDoc / tipoDoc codes
# classeDoc: PY = Payment, SI = Sales Invoice
# tipoDoc: FT = Invoice, FS = Simplified Invoice, FR = Invoice/Receipt,
#          NC = Credit Note, ND = Debit Note, RG = Payment Receipt
PT_AT_DOCUMENT_TYPE_MAPPING = {
    'out_invoice':         {'classeDoc': 'SI', 'tipoDoc': 'FT'},
    'out_receipt':         {'classeDoc': 'SI', 'tipoDoc': 'FS'},
    'out_invoice_receipt': {'classeDoc': 'SI', 'tipoDoc': 'FR'},
    'out_refund':          {'classeDoc': 'SI', 'tipoDoc': 'NC'},
    'debit_note':          {'classeDoc': 'SI', 'tipoDoc': 'ND'},
    'payment_receipt':     {'classeDoc': 'PY', 'tipoDoc': 'RG'},
}

# AT webservice meioProcessamento codes
PT_AT_MEIO_PROCESSAMENTO = 'PI'  # Programa Informático de Faturação
