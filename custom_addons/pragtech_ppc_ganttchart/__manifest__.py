# -*- coding: utf-8 -*-
{
    'name': "Project Planning and Gantt Chart",
    'version': '18.0.1.0.0',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': "www.pragtech.co.in",
    'category': 'Construction',
    'summary': """Created Gantt chart based on hierarchy of project,subproject,wbs,task groups and tasks""",
    'description': """
Project Planning and Gantt Chart
================================
Created Gantt chart based on hierarchy of project,subproject,wbs,task groups and tasks
<keywords>
gantt chart
project planning
construction gantt chart
project controlling
project planning in odoo
gantt chart in odoo 
construction
odoo construction
    """,
    'depends': ['web', 'base', 'pragtech_ppc', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'wizard/wizard_gantt_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pragtech_ppc_ganttchart/static/src/js/widgets.js',
            'pragtech_ppc_ganttchart/static/src/xml/**/*',
        ],
        'web.assets_frontend': [
            'pragtech_ppc_ganttchart/static/src/js/initialization_copy.js',
        ],
    },

    'images': ['images/Animated-Construction-gantchart.gif'],
    'live_test_url': 'https://www.pragtech.co.in/company/proposal-form.html?id=103&name=ppc-gantt-chart',
    'license': 'OPL-1',
    'price': 199,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
}
