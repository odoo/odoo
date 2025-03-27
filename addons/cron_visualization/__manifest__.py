# -*- coding: utf-8 -*-
{
    'name': "Cron Visualization",
    'summary': "Add an automatic refreshing kanban view to visualize cron jobs that are running in your Odoo instance.",
    'description': """Cron Visualization is a module that allows you to visualize the cron jobs that are running in your Odoo instance.""",
    'images': ['static/description/banner.gif'],  # 560x280 px
    'category': 'Technical',
    'version': '0.0.1',
    'author': "Victor",
    'license': 'LGPL-3',
    'price': 0,
    'currency': 'EUR',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',

        'views/cv_ir_cron_history.xml',
        'views/ir_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cron_visualization/static/src/*/*.scss',
            'cron_visualization/static/src/*/*.xml',
            'cron_visualization/static/src/*/*.js',
            'cron_visualization/static/src/backend_style.scss',
        ]
    },
    'installable': True,
    'application': False,
}
