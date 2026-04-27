# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Signatures',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Signature templates from Documents',
    'description': """
Add the ability to create signatures from the document module.
The first element of the selection (in DRM) will be used as the signature attachment.
""",
    'website': ' ',
    'depends': ['documents', 'sign'],

    'data': [
        'data/documents_folder_data.xml',
        'data/ir_action_server_data.xml',
        'data/res_company_data.xml',
        'views/sign_templates.xml',
        'views/res_config_settings.xml',
    ],

    'demo': [
        'demo/documents_document_demo.xml',
    ],

    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
