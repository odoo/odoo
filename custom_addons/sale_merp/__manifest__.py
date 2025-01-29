{
    'name': 'Sales Custom MotionERP',
    'version': '1.0',
    'summary': 'All customization related to sale module',
    'author': 'MotionERP',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',  # Pastikan file ini ada jika perlu akses khusus
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
}