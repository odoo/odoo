{
    'name': "Import/Export electronic orders with UBL",
    'version': '1.0',
    'category': 'Inventory/Purchase',
    'description': """
Allows to export and import formats: UBL Bis 3.
When generating the PDF on the order, the PDF will be embedded inside the xml for all UBL formats. This allows the
receiver to retrieve the PDF with only the xml file.
    """,
    'depends': ['purchase', 'account_edi_ubl_cii'],
    'data': [
        'data/bis3_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
