PT_CERTIFICATION_NUMBER = "9999"  # TODO: Fill with Certificate number provided by the Tax Authority

# Simplified invoice (FS) limits per Portuguese VAT code:
# goods <= 1000 EUR, services <= 100 EUR
PT_SIMPLIFIED_INVOICE_GOODS_LIMIT = 1000.0
PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT = 100.0

# The designation each document type is printed with, as the AT names it (Portaria 302/2016,
# fields 4.1.4.8, 4.2.3.8, 4.3.4.8 and 4.4.4.6), whatever the language of the document. Keyed by
# `l10n_pt_document_type`, over every module that adds a type.
PT_DOCUMENT_TYPE_DESIGNATIONS = {
    'out_invoice': "Fatura",
    'out_receipt': "Fatura simplificada",
    'out_invoice_receipt': "Fatura-recibo",
    'out_refund': "Nota de crédito",
    'debit_note': "Nota de débito",
    'payment_receipt': "Recibo",
    'quotation': "Orçamento",
    'sales_order': "Nota de encomenda",
    'outgoing': "Guia de transporte",
    'internal': "Guia de movimentação de ativos fixos próprios",
    'incoming': "Guia de devolução",
}

# VAT exemption reasons whose base is reported in the QR code's L field rather than as an exempt
# base: operations not subject to VAT, and margin schemes, where the VAT is not shown (QR code
# specification v1.1, section 4; FAQ 4129).
PT_QR_NOT_SUBJECT_EXEMPTION_REASONS = ('M12', 'M13', 'M14', 'M15', 'M99')

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

# AT webservice WSDL URL
PT_AT_WS_WSDL_URL = (
    'https://info.portaldasfinancas.gov.pt/pt/apoio_ao_contribuinte/Outras_entidades/'
    'Suporte_tecnologico/Webservice/Comunicacao_de_series_ATCUD/Documents/Comunicacao_Series.wsdl'
)

# AT webservice SOAP endpoints
PT_AT_WS_ENDPOINT_TEST = 'https://servicos.portaldasfinancas.gov.pt:722/SeriesWSService'
PT_AT_WS_ENDPOINT_PROD = 'https://servicos.portaldasfinancas.gov.pt:422/SeriesWSService'
