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

# The AT's WSDL of its series webservice, shipped as published on its information site
# (info.portaldasfinancas.gov.pt, Comunicacao_de_series_ATCUD/Documents/Comunicacao_Series.wsdl, checked on 2026-11-18,
# md5 dc9e65d2ec420d8bac4a86017a2db61e). Its own address is a placeholder: the endpoints below are used.
PT_AT_WS_WSDL_PATH = 'l10n_pt_at_webservice/data/Comunicacao_Series.wsdl'

PT_AT_WS_ENDPOINT_TEST = 'https://servicos.portaldasfinancas.gov.pt:722/SeriesWSService'
PT_AT_WS_ENDPOINT_PROD = 'https://servicos.portaldasfinancas.gov.pt:422/SeriesWSService'
