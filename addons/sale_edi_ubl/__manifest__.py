{
    'name': "Import electronic orders with UBL",
    'version': '1.0',
    'category': 'Sales/Sales',
    'description': """
Electronic ordering module
===========================

Allows to import formats: UBL Bis 3.
When uploading or pasting Files in order list view with order related data inside XML file or PDF
File with embedded xml data will allow seller to retrieve Order data from Files.
    """,
    'depends': ['sale', 'account_edi_ubl_cii'],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
