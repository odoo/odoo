#  Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Project direct link",
    'version': '1.0',
    'summary': "Link MRP to Project",
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp', 'project'],
    'data': [
        'security/mrp_project_security.xml',
        'views/project_project_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
