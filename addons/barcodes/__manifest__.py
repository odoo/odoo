{
    'name': 'Barcode',
    'version': '2.0',
    'category': 'Hidden',
    'summary': 'Scan and Parse Barcodes',
    'depends': ['web'],
    'data': [
        'data/barcodes_data.xml',
        'views/barcodes_view.xml',
        'security/ir.model.access.csv',
        'views/barcodes_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'post_init_hook': '_assign_default_nomeclature_id',
}
