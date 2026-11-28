# The AT webservice's document class (classeDoc) and type (tipoDoc) of each document type of a series.
# The sale and stock types are those l10n_pt_sale and l10n_pt_stock add; they are plain strings, so
# this module does not depend on either.
# classeDoc: SI = invoices and corrective documents, PY = receipts, WD = working documents,
#            MG = transport documents
PT_AT_DOCUMENT_TYPE_MAPPING = {
    'out_invoice':         {'classeDoc': 'SI', 'tipoDoc': 'FT'},  # Invoice
    'out_receipt':         {'classeDoc': 'SI', 'tipoDoc': 'FS'},  # Simplified invoice
    'out_invoice_receipt': {'classeDoc': 'SI', 'tipoDoc': 'FR'},  # Invoice/receipt
    'out_refund':          {'classeDoc': 'SI', 'tipoDoc': 'NC'},  # Credit note
    'debit_note':          {'classeDoc': 'SI', 'tipoDoc': 'ND'},  # Debit note
    'payment_receipt':     {'classeDoc': 'PY', 'tipoDoc': 'RG'},  # Other receipts
    'quotation':           {'classeDoc': 'WD', 'tipoDoc': 'OR'},  # Quotation
    'sales_order':         {'classeDoc': 'WD', 'tipoDoc': 'NE'},  # Sales order (nota de encomenda)
    'outgoing':            {'classeDoc': 'MG', 'tipoDoc': 'GT'},  # Transport guide
    'internal':            {'classeDoc': 'MG', 'tipoDoc': 'GA'},  # Own fixed assets movement guide
    'incoming':            {'classeDoc': 'MG', 'tipoDoc': 'GD'},  # Return note (guia de devolução)
}

# AT webservice meioProcessamento codes
PT_AT_MEIO_PROCESSAMENTO = 'PI'  # Programa Informático de Faturação

# The AT's public key (KpubSA, the key of its authentication system), as the X.509 certificate the AT
# sends to software producers: the same for every taxpayer, it encrypts each request's AES key (Nonce).
# PLACEHOLDER: this file is the certificate of the local fake AT (CN "Fake AT public key", valid until
# 2036-11-15, SHA-256 BD:3B:A3:1B:…:7E:27:F7:9E), to be replaced by the certificate the AT sends.
PT_AT_WS_PUBLIC_KEY_PATH = 'l10n_pt_at_webservice/data/at_public_key.pem'
