{
    'name': 'DRS Extrusion Production Management',
    'version': '18.0.1.3.0',
    'sequence': 1,
    'summary': 'Manage Daily DRS Machine Extrusion, Personnel, and Dashboard',
    'description': """
        Advanced Manufacturing module to track DRS Roll Machine operations, 
        shift details, quality metrics, heating zone temperatures, Excel exports, 
        and an interactive OWL Dashboard.
    """,
    'category': 'Manufacturing/Manufacturing',
    'author': 'Your Company',
    'depends': ['base', 'hr', 'mrp', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/drs_dashboard_action.xml',
        'wizard/drs_excel_wizard_views.xml',
        'views/drs_production_views.xml',
        'views/drs_personnel_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mrp_drs_production/static/src/css/drs_dashboard.css',
            'mrp_drs_production/static/src/js/drs_dashboard.js',
            'mrp_drs_production/static/src/xml/drs_dashboard.xml',
            'mrp_drs_production/static/src/js/supervisor_dashboard.js',
            'mrp_drs_production/static/src/xml/supervisor_dashboard.xml',
            'mrp_drs_production/static/src/js/technician_dashboard.js',
            'mrp_drs_production/static/src/xml/technician_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
