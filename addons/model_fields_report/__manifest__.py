# -*- coding: utf-8 -*-
{
    'name': 'Model Fields Report',
    'category': 'Technical',
    'summary': 'Report showing field count per model using PostgreSQL view',
    'description': """
        This module provides a report that displays the number of fields 
        for each model in the system, using a PostgreSQL view for performance.
    """,
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/model_fields_count_views.xml',
        'data/ir_cron_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'model_fields_report/static/src/js/refresh_button.js',
            'model_fields_report/static/src/xml/refresh_button.xml',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

