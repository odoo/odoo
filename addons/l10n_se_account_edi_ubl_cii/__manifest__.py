{
    'name': 'Sweden - PEPPOL BIS 3.0 E-Invoicing',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Extends PEPPOL BIS 3.0 UBL for Swedish national validation rules',
    'description': """
Adds support for Swedish-specific validation rules and data elements for PEPPOL BIS Billing 3.0 UBL exports in Odoo 17.

Key features:
- SE national rules (SE-R-001 to SE-R-013)
- Support for RequisitionDocumentReference and OrderReference
- Automatic "Godkänd för F-skatt" handling
- Validation of VAT, organisation number, and payment means
""",
    'author': 'XCLUDE',
    'license': 'LGPL-3',
    'depends': [
        'account_edi_ubl_cii',
    ],
    'installable': True,
}
