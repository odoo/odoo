# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Fleet',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Fleet from documents',
    'description': """
Adds fleet data to documents
""",
    'website': ' ',
    'depends': ['documents', 'fleet'],
    'data': [
        'data/documents_folder_data.xml',
        'data/documents_tag_data.xml',
        'data/ir_actions_server_data.xml',
        'data/res_company_data.xml',
        'views/fleet_vehicle_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
