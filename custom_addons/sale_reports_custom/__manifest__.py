{
    'name': 'Goca, Reporte Personalizado para Cotizaciones',
    'version': '1.0',
    'author': 'GOCA C.A.',
    'category': 'Sales',
    'summary': 'Reporte Personalizado para cotizaciones y facturas',
    'depends': ['sale'],
    'data': [
        'report/report_saleorder_inheritance.xml',
        'report/report_invoice_inheritance.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}