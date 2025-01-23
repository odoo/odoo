{
    'name': "Import/Export Electronic Orders with UBL",
    'category': 'Accounting/Accounting',
    'description': """
        Electronic Ordering Module
        ===========================
        Enables the import and export of UBL BIS 3 formats.
        Users can upload or paste files in the order list view containing
        order-related data in XML or PDF formats.
        For PDF files with embedded XML data, the system retrieves and
        processes the order information seamlessly.
    """,
    'depends': ['account_edi_ubl_cii'],
    'data': [
        'data/bis3_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
