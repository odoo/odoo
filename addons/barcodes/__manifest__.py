{
    'name': 'Barcode',
    'version': '2.0',
    'category': 'Extra Tools',
    'summary': 'Barcodes Scanning and Parsing',
    'depends': ['web'],
    'data': [
        'data/barcodes_data.xml',
        'views/barcodes_view.xml',
        'security/ir.model.access.csv',
        'views/barcodes_templates.xml',
        'views/res_company.xml',
    ],
    'installable': True,
    'auto_install': False,
    'post_init_hook': '_assign_default_nomeclature_id',
}
