# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Approvals',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Approval from documents',
    'description': """
Adds approvals data to documents
""",
    'website': ' ',
    'depends': ['documents', 'approvals'],
    'data': [
        "views/res_config_settings_views.xml",
        "views/approval_request_views.xml",
        "data/documents_folder_data.xml",
        "data/res_company_data.xml"
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
