# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Product',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Products from Documents',
    'description': """
Adds the ability to create products from the document module and adds the
option to send products' attachments to the documents app.
""",
    'website': ' ',
    'depends': ['documents', 'product'],
    'data': [
        'data/documents_folder_data.xml',
        'data/documents_tag_data.xml',
        'data/ir_actions_server_data.xml',
        'data/res_company_data.xml',
        'views/res_config_settings_views.xml',
        'views/documents_document_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
