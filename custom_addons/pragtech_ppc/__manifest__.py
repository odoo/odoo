# -*- coding: utf-8 -*-
{
    'name': 'Construction Project Planning and Controlling',
    'version': '18.0.1.0.0',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': "www.pragtech.co.in",
    'category': 'Construction',
    'description': """
        Construction Project Planning and Controlling
        =============================================
        Project Planning, budgeting, costing
        <keywords>
        construction project planning and controlling
        project planning and controlling
        project planning
        project controlling
        construction
        construction management
        construction app
        construction module
    """,

    'depends': ['product', 'project', 'stock', 'account'],
    'data': [
        'views/execution_menu.xml',
        'views/stages_view.xml',
        'data/stage_master_data.xml',
        'views/mail_message_view.xml',
        'wizard/stage_transaction_wizard.xml',
        'views/material_view.xml',
        'views/task_library_view.xml',
        'views/labour_view.xml',
        'views/category_view.xml',
        'security/access_rules.xml',
        'security/ir.model.access.csv',
        'views/project_view.xml',
        'views/task_view.xml',
        'views/sub_project_view.xml',
        'views/category_budget.xml',
        'wizard/task_scheduler_wizard.xml',
        'views/sequence_view.xml',
        'report/report.xml',
        'report/groupwise_cost_variance_report.xml',
        'report/category_budget_report.xml',
        'views/res_usr.xml',
    ],
    'images': ['images/Animated-Construction-ppc.gif'],

    'live_test_url': 'https://www.pragtech.co.in/company/proposal-form.html?id=103&name=Odoo-Construction-Management',
    'license': 'LGPL-3',
    'price': 249,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
}

