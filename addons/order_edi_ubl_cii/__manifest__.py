{
    'name': "Import/Export electronic orders with UBL",
    'category': 'Accounting/Accounting',
    'description': """
        Electronic ordering module
        ===========================

        Allows to import/export formats: UBL Bis 3.
        When uploading or pasting Files in order list view with order related data inside XML file or PDF
        File with embedded xml data will allow user to retrieve Order data from Files.
    """,
    'depends': ['account_edi_ubl_cii'],
    'data': [
        'data/bis3_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
