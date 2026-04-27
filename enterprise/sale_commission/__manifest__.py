# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sale Commission',
    'version': '1.0',
    'category': 'Sales/Commission',
    'sequence': 105,
    'summary': "Manage your salespersons' commissions",
    'description': """
    """,
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/sale_commission_settings.xml',
        'wizard/sale_commission_add_multiple_user.xml',
        'views/sale_commission_plan_view.xml',
        'views/sale_commission_achievement_view.xml',
        'views/sale_commission_forecast_view.xml',
        'views/crm_team_views.xml',
        'report/commission_report.xml',
        'report/achievement_report.xml',
        'views/sale_commission_menu.xml',
    ],
    'demo': [
        'data/sale_commission_demo.xml'
    ],
    'installable': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'sale_commission/static/src/js/commission_plan_graph/commission_plan_graph.js',
            'sale_commission/static/src/js/commission_plan_graph/commission_plan_graph.scss',
            'sale_commission/static/src/js/commission_plan_graph/commission_plan_graph.xml',
        ],
    }
}
