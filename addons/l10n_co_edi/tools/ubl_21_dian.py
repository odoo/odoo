# DIAN UBL 2.1 Templates for Colombian Electronic Invoicing
#
# These templates extend the standard UBL 2.1 templates with DIAN-specific
# elements required for Colombian electronic invoicing (facturacion electronica).
# They enforce the correct element ordering per DIAN Technical Annex v1.9.

import odoo.addons.account_edi_ubl_cii.tools.ubl_21_common as cac
from odoo.addons.account_edi_ubl_cii.tools import Invoice, CreditNote

# -------------------------------------------------------------------------
# DIAN Extension Templates
# -------------------------------------------------------------------------

DianExtensions = {
    'sts:InvoiceControl': {
        'sts:InvoiceAuthorization': {},
        'sts:AuthorizationPeriod': {
            'cbc:StartDate': {},
            'cbc:EndDate': {},
        },
        'sts:AuthorizedInvoices': {
            'sts:Prefix': {},
            'sts:From': {},
            'sts:To': {},
        },
    },
    'sts:InvoiceSource': {
        'cbc:IdentificationCode': {},
    },
    'sts:SoftwareProvider': {
        'sts:ProviderID': {},
        'sts:SoftwareID': {},
    },
    'sts:SoftwareSecurityCode': {},
    'sts:AuthorizationProvider': {
        'sts:AuthorizationProviderID': {},
    },
    'sts:QRCode': {},
}

UBLExtension = {
    'ext:ExtensionContent': {
        'sts:DianExtensions': DianExtensions,
    },
}

UBLExtensions = {
    'ext:UBLExtension': UBLExtension,
}

# -------------------------------------------------------------------------
# DIAN Invoice Template (extends standard UBL 2.1 Invoice)
# -------------------------------------------------------------------------

DianInvoice = dict(Invoice)
DianInvoice['ext:UBLExtensions'] = UBLExtensions

# -------------------------------------------------------------------------
# DIAN Credit Note Template (extends standard UBL 2.1 CreditNote)
# -------------------------------------------------------------------------

DianCreditNote = dict(CreditNote)
DianCreditNote['ext:UBLExtensions'] = UBLExtensions
